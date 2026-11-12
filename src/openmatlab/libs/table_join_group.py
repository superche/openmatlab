"""Joins and grouping (M10 T-E6, #696).

``join``/``innerjoin``/``outerjoin`` match rows on key variables by typed per-row keys; outputs are
sorted by key (inner/outer) or keep the left table's order (join). Unmatched outer rows are filled
with each type's missing value (NaN, NaT, '', <missing>, <undefined>, 0 for integers, false for
logical). ``findgroups``/``splitapply``/``groupsummary``/``groupcounts`` number groups by the sorted
unique combinations of the grouping variables (rank keys from ``table_utils``).

``groupsummary`` and ``groupcounts`` treat a cellstr ``''`` and a string ``<missing>`` as
missing group keys, the same entries ``ismissing`` reports (#1060). A string ``""`` is a
real key. ``findgroups`` still uses ``rank_columns`` directly. Char blanks are not part of
this path.

``groupsummary(..., 'IncludeEmptyGroups', true)`` (M17 #742) also emits empty groups: every
category of a categorical grouping variable, both ``false`` and ``true`` of a logical one, and
every combination of those possible values. ``groupcounts`` uses the same rule (#1055). Groups
are ordered like the default path: column by column, with a missing value sorting last inside
that column.

``findgroups(..., 'IncludeMissing', true)`` (#1054) numbers a missing key instead of writing
NaN and leaving it out of ``ID`` / ``TID``. The default stays the documented one: NaN in ``G``,
omitted from the identifiers. ``splitapply`` stacks a table returned for each group.
``grouptransform`` and ``groupfilter`` keep the input row order (#1055).

A multi-column grouping variable is one key — the whole row — so the flag does not invent a
Cartesian product of its columns (#1053). Binning runs before that grouping. The #1053 set is
numeric edges, a positive bin count, ``IncludedEdge``, and the datetime schemes whose labels the
documentation names (``dayname``, ``monthname``, and the ``*of*`` units). #1070 adds calendar-width
units, a duration or calendarDuration width, datetime edges, and several schemes on one variable.
Array input returns ``[B,BG,BC]``.

``join`` accepts ``'KeepOneCopy'`` (also ``innerjoin`` / ``outerjoin``) and ``'KeepKeys'``.
``'Keys','RowNames'`` (and ``'Row'``) matches row names. Cellstr and string keys compare as
text; double and integer keys compare as numbers (#1052). A duplicate non-key name is
suffixed with the input's variable name, or ``_left`` / ``_right`` when that input is an
expression (#1056).
"""

from __future__ import annotations

import itertools
import math

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.libs.table_utils import _col_rows, _ev, _opts, _row_keys, _sort_order, rank_columns
from openmatlab.runtime.table_value import TableValue, _cv, _err, height_of, is_text, text, texts


def _is_table(v):
    return getattr(v, "is_table", False)


def _num_col(a):
    return NDArrayValue(np.asarray(a, dtype=float).reshape(-1, 1))


# =====================================================================
# missing-filled row selection
# =====================================================================
def _missing_row(c, w):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    if getattr(c, "is_categorical", False):
        return c.like(np.zeros((1, w), dtype=np.int64))
    if isinstance(c, DatetimeValue):
        return DatetimeValue(np.full((1, w), np.nan), c.fmt)
    if isinstance(c, DurationValue):
        return DurationValue(np.full((1, w), np.nan), c.fmt)
    if getattr(c, "is_string", False):
        from openmatlab.runtime import string_array as sa

        return sa.make(np.array([[None] * w], dtype=object))
    if isinstance(c, CellValue):
        return CellValue(rows=(tuple(CharValue("") for _ in range(w)),))
    if isinstance(c, CharValue):
        return CharValue(" " * w)
    if hasattr(c, "backend_buffer") and not getattr(c, "is_object", False):
        a = np.asarray(c.backend_buffer())
        if a.dtype == np.bool_:
            return NDArrayValue(np.zeros((1, w), dtype=bool))
        return NDArrayValue(np.full((1, w), np.nan))
    raise _err(f"outerjoin: cannot fill unmatched rows of a '{c.matlab_class()}' variable.",
               "MATLAB:table:join:UnsupportedFillType")


def _width(c, n):
    sh = c.shape if hasattr(c, "shape") else (n, 1)
    return int(np.prod(sh)) // n if n else int(sh[1]) if len(sh) > 1 else 1


def take_filled(c, n, rows):
    """Rows of variable ``c`` (height n); -1 entries become the type's missing value."""
    rows = np.asarray(rows, dtype=int)
    if not np.any(rows < 0):
        return _col_rows(c, rows) if len(rows) else _col_rows(c, np.zeros(0, dtype=int))
    w = max(_width(c, n), 1) if n else 1
    ext = _ev().concat_values([[c], [_missing_row(c, w)]]) if n else _missing_row(c, w)
    return _col_rows(ext, np.where(rows < 0, n, rows))


# =====================================================================
# joins
# =====================================================================
def _arg_names(k):
    from openmatlab.libs.table_builtins import _caller_arg_names

    return _caller_arg_names(k)


# ``None`` in a key list is the row-name vector (``'Row'`` / ``'RowNames'``), not a variable.
_ROW_KEY = None


def _is_row_key_name(name):
    return name in ("Row", "RowNames")


def _key_label(T, item):
    return "Row" if item is _ROW_KEY else T.names[item]


def _as_keys(T, spec, fn):
    """Variable indices, with ``None`` where the spec names the row-name vector."""
    names = texts(spec)
    if names is None:
        return T.var_sel(spec)
    out = []
    for s in names:
        if _is_row_key_name(s):
            if not T.rownames:
                raise _err(f"{fn}: the table has no row names to use as a key.", f"MATLAB:table:{fn}:NoRowNames")
            out.append(_ROW_KEY)
        else:
            out.append(T.var_index(s))
    return out


def _key_spec(A, B, opts, fn):
    if "keys" in opts and ("leftkeys" in opts or "rightkeys" in opts):
        raise _err(f"{fn}: specify 'Keys', or 'LeftKeys' and 'RightKeys', not both.", f"MATLAB:table:{fn}:ConflictingKeys")
    if "keys" in opts:
        lk = _as_keys(A, opts["keys"], fn)
        rk = []
        for item in lk:
            if item is _ROW_KEY:
                if not B.rownames:
                    raise _err(f"{fn}: the table has no row names to use as a key.", f"MATLAB:table:{fn}:NoRowNames")
                rk.append(_ROW_KEY)
            else:
                rk.append(B.var_index(A.names[item]))
    elif "leftkeys" in opts or "rightkeys" in opts:
        if not ("leftkeys" in opts and "rightkeys" in opts):
            raise _err(f"{fn}: 'LeftKeys' and 'RightKeys' must be given together.", f"MATLAB:table:{fn}:MissingKeys")
        lk, rk = _as_keys(A, opts["leftkeys"], fn), _as_keys(B, opts["rightkeys"], fn)
    else:
        common = [n for n in A.names if n in B.names]
        if not common:
            raise _err(f"{fn}: the tables have no variables in common to use as keys. Specify 'Keys'.",
                       f"MATLAB:table:{fn}:NoCommonKeys")
        lk = [A.var_index(n) for n in common]
        rk = [B.var_index(n) for n in common]
    if len(lk) != len(rk) or not lk:
        raise _err(f"{fn}: the left and right key lists must have the same nonzero length.", f"MATLAB:table:{fn}:KeyCountMismatch")
    return lk, rk


def _row_name_col(T):
    from openmatlab.runtime.table_value import cellstr_col

    return cellstr_col(T.rownames)


def _key_col(T, item):
    return _row_name_col(T) if item is _ROW_KEY else T.cols[item]


def _keys_as(T, idx, names):
    return TableValue(list(names), [_key_col(T, i) for i in idx], T.nrows)


def _match(A, B, lk, rk, fn):
    knames = [f"k{j}" for j in range(len(lk))]
    KA, KB = _keys_as(A, lk, knames), _keys_as(B, rk, knames)
    for j in range(len(lk)):
        if _row_key_kind(KA.cols[j]) != _row_key_kind(KB.cols[j]):
            raise _err(f"{fn}: the key variables '{_key_label(A, lk[j])}' and '{_key_label(B, rk[j])}' "
                       "have incompatible types.", f"MATLAB:table:{fn}:KeyTypeMismatch")
    return KA, KB, _row_keys(KA), _row_keys(KB)


def _row_key_kind(c):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    if getattr(c, "is_categorical", False):
        return "cat"
    if isinstance(c, DatetimeValue):
        return "datetime"
    if isinstance(c, DurationValue):
        return "duration"
    if getattr(c, "is_string", False) or isinstance(c, (CellValue, CharValue)):
        return "text"
    return "num"


def _text_key_col(c, n):
    """One string column per cellstr key, so it can be concatenated with a string key."""
    from openmatlab.runtime import string_array as sa
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    if getattr(c, "is_string", False) or n == 0 or not isinstance(c, CellValue):
        return c
    w = max(c.shape[1], 1)
    grid = np.empty((n, w), dtype=object)
    for r in range(n):
        for j in range(w):
            e = c.rows[r][j]
            grid[r, j] = e.text if isinstance(e, CharValue) else ""
    return sa.make(grid)


def _same_text_storage(a, b):
    if getattr(a, "is_string", False) or getattr(b, "is_string", False):
        return getattr(a, "is_string", False) and getattr(b, "is_string", False)
    return type(a) is type(b)


def _align_text_keys(KA, KB):
    """Homogenize mixed text keys before the sort concatenates them.

    Double and integer keys already concatenate. Cellstr and string do not:
    the combined column is no longer a cell array of character vectors, and
    ranking rejects it. Matching itself already compares both as text.
    """
    cols_a, cols_b, changed = [], [], False
    for ca, cb in zip(KA.cols, KB.cols):
        if _row_key_kind(ca) == "text" and not _same_text_storage(ca, cb):
            ca, cb = _text_key_col(ca, KA.nrows), _text_key_col(cb, KB.nrows)
            changed = True
        cols_a.append(ca)
        cols_b.append(cb)
    if not changed:
        return KA, KB
    return TableValue(list(KA.names), cols_a, KA.nrows), TableValue(list(KB.names), cols_b, KB.nrows)


def _sorted_pairs(pairs, KA, KB):
    """Sort (ia, ib) pairs by their key values (MATLAB orders join output by key)."""
    if not pairs:
        return pairs
    KA, KB = _align_text_keys(KA, KB)
    both = _ev().concat_values([[KA], [KB]])
    ranks = [r for c in both.cols for r in rank_columns(c, both.nrows)]
    src = np.array([ia if ia >= 0 else KA.nrows + ib for ia, ib in pairs])
    keys = [r[src] for r in ranks]
    order = _sort_order(keys, ["ascend"] * len(keys))
    return [pairs[i] for i in order]


def _unique_names(names):
    from openmatlab.runtime.table_value import check_names

    check_names(names)
    return names


def _suffix_names(left, right, an, bn, rename_all=()):
    """Suffix a name that occurs on both sides.

    The suffix is the caller's variable name (``Var1_A`` beside ``Var1_B`` in
    the ``join`` examples). An expression has no name (``inputname`` is empty),
    so it uses ``left`` or ``right``. When both suffixes are the same string,
    as in ``join(T, T)``, the left one gains ``_1``.
    """
    sa = an or "left"
    sb = bn or "right"
    if sa == sb:
        sa = sa + "_1"
    sa, sb = "_" + sa, "_" + sb
    L, R = list(left), list(right)
    for i, n in enumerate(L):
        if n in R or n in rename_all:
            j = R.index(n) if n in R else None
            L[i] = n + sa
            if j is not None:
                R[j] = n + sb
    return L, R


def _kept_names(A, B, opts, fn):
    """``'KeepOneCopy'`` names: drop the right-hand copy of each."""
    if "keeponecopy" not in opts:
        return set()
    names = texts(opts["keeponecopy"])
    if not names:
        raise _err(f"{fn}: 'KeepOneCopy' must name at least one variable.", f"MATLAB:table:{fn}:KeepOneCopy")
    for n in names:
        if n not in A.names or n not in B.names:
            raise _err(f"{fn}: 'KeepOneCopy' variable '{n}' must occur in both tables.",
                       f"MATLAB:table:{fn}:KeepOneCopy")
    return set(names)


def _drop_kept(idx, T, kept):
    return [j for j in idx if T.names[j] not in kept] if kept else list(idx)


def _nonkey(idx, keys):
    ban = {i for i in keys if i is not _ROW_KEY}
    return [j for j in idx if j not in ban]


def _result_rownames(A, B, lk, rk, ia, ib):
    """Row names of a join whose key list uses the row-name vector.

    ``join`` keeps the left table's row names itself. ``innerjoin`` and
    ``outerjoin`` attach them only when row names are a key: the left name
    when that row is present, otherwise the right name.
    """
    left = any(i is _ROW_KEY for i in lk)
    right = any(i is _ROW_KEY for i in rk)
    if not left and not right:
        return None
    out = []
    for i, j in zip(np.asarray(ia).tolist(), np.asarray(ib).tolist()):
        if left and i >= 0:
            out.append(A.rownames[i])
        elif right and j >= 0:
            out.append(B.rownames[j])
        else:
            return None
    return out


def _cast_text_fill(dst, src):
    """Write a text key into ``dst``'s storage when the other side differs."""
    if _row_key_kind(dst) != "text" or _row_key_kind(src) != "text" or _same_text_storage(dst, src):
        return src
    n = height_of(src)
    if getattr(dst, "is_string", False):
        return _text_key_col(src, n)
    from openmatlab.runtime import string_array as sa
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    g = np.asarray(sa.to_grid(src), dtype=object).reshape(n, -1)
    rows = tuple(tuple(CharValue("" if g[r, j] is None else str(g[r, j])) for j in range(g.shape[1]))
                 for r in range(n))
    return CellValue(rows=rows) if rows else CellValue(rows=())


def _vars_opt(T, opts, key, default):
    return T.var_sel(opts[key]) if key in opts else default


def _innerjoin(args, *, nargout=1):
    data, opts = _opts(args, ("keys", "leftkeys", "rightkeys", "leftvariables", "rightvariables", "keeponecopy"),
                       "innerjoin")
    if len(data) != 2 or not (_is_table(data[0]) and _is_table(data[1])):
        raise _err("innerjoin: the first two inputs must be tables.", "MATLAB:table:innerjoin:InvalidInput")
    A, B = data
    an, bn = _arg_names(2)
    lk, rk = _key_spec(A, B, opts, "innerjoin")
    KA, KB, ka, kb = _match(A, B, lk, rk, "innerjoin")
    pos = {}
    for j, k in enumerate(kb):
        pos.setdefault(k, []).append(j)
    pairs = [(i, j) for i, k in enumerate(ka) for j in pos.get(k, [])]
    pairs = _sorted_pairs(pairs, KA, KB)
    kept = _kept_names(A, B, opts, "innerjoin")
    lv = _vars_opt(A, opts, "leftvariables", list(range(len(A.names))))
    rv = _drop_kept(_vars_opt(B, opts, "rightvariables", _nonkey(range(len(B.names)), rk)), B, kept)
    ia = np.array([p[0] for p in pairs], dtype=int)
    ib = np.array([p[1] for p in pairs], dtype=int)
    Ln, Rn = _suffix_names([A.names[i] for i in lv], [B.names[j] for j in rv], an, bn)
    cols = [take_filled(A.cols[i], A.nrows, ia) for i in lv] + [take_filled(B.cols[j], B.nrows, ib) for j in rv]
    out = TableValue(_unique_names(Ln + Rn), cols, len(pairs), _result_rownames(A, B, lk, rk, ia, ib))
    return (out, _num_col(ia + 1), _num_col(ib + 1))[:max(1, nargout)]


def _outerjoin(args, *, nargout=1):
    data, opts = _opts(args, ("keys", "leftkeys", "rightkeys", "leftvariables", "rightvariables", "type", "mergekeys",
                              "keeponecopy"), "outerjoin")
    if len(data) != 2 or not (_is_table(data[0]) and _is_table(data[1])):
        raise _err("outerjoin: the first two inputs must be tables.", "MATLAB:table:outerjoin:InvalidInput")
    A, B = data
    an, bn = _arg_names(2)
    kind = text(opts["type"]).lower() if "type" in opts and is_text(opts["type"]) else ("full" if "type" not in opts else "")
    if kind not in ("full", "left", "right"):
        raise _err("outerjoin: 'Type' must be 'full', 'left' or 'right'.", "MATLAB:table:outerjoin:InvalidType")
    merge = bool(np.asarray(opts["mergekeys"].backend_buffer()).reshape(-1)[0]) if "mergekeys" in opts else False
    lk, rk = _key_spec(A, B, opts, "outerjoin")
    KA, KB, ka, kb = _match(A, B, lk, rk, "outerjoin")
    pos = {}
    for j, k in enumerate(kb):
        pos.setdefault(k, []).append(j)
    pairs = []
    matched_b = set()
    for i, k in enumerate(ka):
        js = pos.get(k, [])
        if js:
            for j in js:
                pairs.append((i, j))
                matched_b.add(j)
        elif kind in ("full", "left"):
            pairs.append((i, -1))
    if kind in ("full", "right"):
        pairs += [(-1, j) for j in range(B.nrows) if j not in matched_b]
    pairs = _sorted_pairs(pairs, KA, KB)
    ia = np.array([p[0] for p in pairs], dtype=int)
    ib = np.array([p[1] for p in pairs], dtype=int)
    kept = _kept_names(A, B, opts, "outerjoin")
    lv = _vars_opt(A, opts, "leftvariables", list(range(len(A.names))))
    rv = _drop_kept(_vars_opt(B, opts, "rightvariables", list(range(len(B.names)))), B, kept)
    names, cols = [], []
    # A row-name key is not a variable. Only variable/variable pairs become one merged column.
    var_pairs = [(i, j) for i, j in zip(lk, rk) if i is not _ROW_KEY and j is not _ROW_KEY]
    if merge:
        left_keys = {i for i, _j in var_pairs}
        right_keys = {j for _i, j in var_pairs}
        lv_nokey = [i for i in lv if i not in left_keys]
        rv_nokey = [j for j in rv if j not in right_keys]
        key_names = [A.names[i] if A.names[i] == B.names[j] else f"{A.names[i]}_{B.names[j]}" for i, j in var_pairs]
        key_cols = []
        for i, j in var_pairs:
            from_a = take_filled(A.cols[i], A.nrows, ia)
            from_b = take_filled(B.cols[j], B.nrows, ib)
            need_b = np.flatnonzero(ia < 0)
            if need_b.size:
                from openmatlab.runtime.table_subs import ix_asgn
                from openmatlab.runtime.table_value import _idx_value

                sub = _cast_text_fill(from_a, _col_rows(from_b, need_b))
                from_a = ix_asgn(_ev(), from_a, [_idx_value(need_b), None], sub)
            key_cols.append(from_a)
        Ln, Rn = _suffix_names([A.names[i] for i in lv_nokey], [B.names[j] for j in rv_nokey], an, bn)
        names = key_names + Ln + Rn
        cols = key_cols + [take_filled(A.cols[i], A.nrows, ia) for i in lv_nokey] + \
            [take_filled(B.cols[j], B.nrows, ib) for j in rv_nokey]
    else:
        Ln, Rn = _suffix_names([A.names[i] for i in lv], [B.names[j] for j in rv], an, bn)
        names = Ln + Rn
        cols = [take_filled(A.cols[i], A.nrows, ia) for i in lv] + [take_filled(B.cols[j], B.nrows, ib) for j in rv]
    out = TableValue(_unique_names(names), cols, len(pairs), _result_rownames(A, B, lk, rk, ia, ib))
    return (out, _num_col(np.where(ia < 0, 0, ia + 1)), _num_col(np.where(ib < 0, 0, ib + 1)))[:max(1, nargout)]


def _join(args, *, nargout=1):
    data, opts = _opts(args, ("keys", "leftkeys", "rightkeys", "leftvariables", "rightvariables", "keepkeys",
                              "keeponecopy"), "join")
    if len(data) != 2 or not (_is_table(data[0]) and _is_table(data[1])):
        raise _err("join: the first two inputs must be tables.", "MATLAB:table:join:InvalidInput")
    A, B = data
    an, bn = _arg_names(2)
    lk, rk = _key_spec(A, B, opts, "join")
    KA, KB, ka, kb = _match(A, B, lk, rk, "join")
    pos = {}
    for j, k in enumerate(kb):
        if k in pos:
            raise _err("join: the key variables of the right table must have unique values. Use innerjoin or outerjoin "
                       "for many-to-one matches.", "MATLAB:table:join:DuplicateRightKeys")
        pos[k] = j
    ib = []
    for k in ka:
        if k not in pos:
            raise _err("join: the right table must contain a row for every key value in the left table. Use "
                       "innerjoin or outerjoin to drop or fill unmatched rows.", "MATLAB:table:join:LeftKeyValueNotFound")
        ib.append(pos[k])
    ib = np.array(ib, dtype=int)
    kept = _kept_names(A, B, opts, "join")
    # Default right variables omit the key. 'KeepKeys' keeps those columns too.
    right_default = list(range(len(B.names))) if _flag(opts, "keepkeys", False, "join") else _nonkey(range(len(B.names)), rk)
    lv = _vars_opt(A, opts, "leftvariables", list(range(len(A.names))))
    rv = _drop_kept(_vars_opt(B, opts, "rightvariables", right_default), B, kept)
    Ln, Rn = _suffix_names([A.names[i] for i in lv], [B.names[j] for j in rv], an, bn)
    cols = [A.cols[i] for i in lv] + [take_filled(B.cols[j], B.nrows, ib) for j in rv]
    out = TableValue(_unique_names(Ln + Rn), cols, A.nrows, A.rownames)
    return (out, _num_col(ib + 1))[:max(1, nargout)]


# =====================================================================
# grouping
# =====================================================================
def _grouping_ranks(col, n):
    """``rank_columns``, with cellstr ``''`` and string ``<missing>`` marked NaN.

    ``rank_columns`` already ranks string ``<missing>`` last. A cell array of character
    vectors ranks ``''`` as a real key, so it sorts first. ``ismissing`` is the rule for
    both. A blank char vector inside a cell (``' '``) stays present. Char columns are
    left to ``rank_columns`` (#1058).
    """
    ranks = rank_columns(col, n)
    if n == 0 or not ranks:
        return ranks
    from openmatlab.runtime.cell_value import CellValue

    if not isinstance(col, CellValue) and not getattr(col, "is_string", False):
        return ranks
    from openmatlab.libs.missing_builtins import missing_mask

    mask = np.asarray(missing_mask(col), dtype=bool).reshape(n, len(ranks))
    out = []
    for j, r in enumerate(ranks):
        r = np.array(r, dtype=float, copy=True)
        r[mask[:, j]] = np.nan
        out.append(r)
    return out


def group_numbers(cols, n, include_missing, ranker=rank_columns):
    """(G as float array with NaN for missing groups, first-row index per group in group order).

    ``findgroups`` uses ``rank_columns``. ``groupsummary`` and ``groupcounts`` pass
    ``_grouping_ranks`` so a cellstr ``''`` is a missing key.
    """
    keys = []
    for c in cols:
        keys += ranker(c, n)
    if not keys:
        return np.ones(n), np.array([0]) if n else np.zeros(0, dtype=int)
    K = np.column_stack([np.where(np.isnan(k), np.inf, k) for k in keys])
    miss = np.any(np.column_stack([np.isnan(k) for k in keys]), axis=1)
    order = _sort_order(keys, ["ascend"] * len(keys))
    G = np.full(n, np.nan)
    first = []
    prev = None
    g = 0
    for i in order:
        if miss[i] and not include_missing:
            continue
        row = tuple(K[i])
        if row != prev:
            g += 1
            first.append(i)
            prev = row
        G[i] = g
    return G, np.array(first, dtype=int)


def _orient(a, like_row):
    a = np.asarray(a, float)
    return NDArrayValue(a.reshape(1, -1) if like_row else a.reshape(-1, 1))


def _findgroups(args, *, nargout=1):
    data, opts = _opts(args, ("includemissing",), "findgroups")
    if not data:
        raise _err("findgroups: not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    include_missing = _flag(opts, "includemissing", False, "findgroups")
    first = data[0]
    like_row = (not _is_table(first) and hasattr(first, "shape") and len(first.shape) == 2 and first.shape[0] == 1
                and first.shape[1] > 1 and not is_text(first))
    cols = []
    for g in data:
        if _is_table(g):
            cols += list(g.cols)
        else:
            if hasattr(g, "shape") and len(g.shape) == 2 and g.shape[0] == 1 and g.shape[1] > 1 and not is_text(g):
                g = _transpose(g)
            cols.append(g)
    ns = {height_of(c) for c in cols}
    if len(ns) != 1:
        raise _err("findgroups: the grouping variables must have the same number of rows.",
                   "MATLAB:findgroups:GroupVarsLengthMismatch")
    n = ns.pop()
    G, firsts = group_numbers(cols, n, include_missing=include_missing)
    outs = [_orient(G, like_row)]
    if _is_table(first) and len(data) == 1:
        T = first
        outs.append(TableValue(T.names, [_col_rows(c, firsts) for c in T.cols], len(firsts)))
    else:
        for c in cols:
            v = _col_rows(c, firsts)
            outs.append(_transpose(v) if like_row else v)
    return tuple(outs[:max(1, nargout)])


def _transpose(v):
    if hasattr(v, "transpose_value"):
        return v.transpose_value()
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(v, CellValue):
        return CellValue(rows=tuple(zip(*v.rows)))
    if getattr(v, "is_string", False):
        from openmatlab.runtime import string_array as sa

        return sa.make(sa.to_grid(v).T)
    return NDArrayValue(np.asarray(v.backend_buffer()).T.copy())


def _splitapply(args, *, nargout=1):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if len(args) < 3:
        raise _err("splitapply: expected splitapply(func, X, G).", "MATLAB:narginchk:notEnoughInputs")
    fh = args[0]
    if not isinstance(fh, FunctionHandleValue):
        raise _err("splitapply: the first input must be a function handle.", "MATLAB:splitapply:InvalidFunction")
    Gv = args[-1]
    if getattr(Gv, "is_object", False) or not hasattr(Gv, "backend_buffer") or is_text(Gv):
        raise _err("splitapply: the group numbers must be a vector of positive integers (see findgroups).",
                   "MATLAB:splitapply:InvalidGroupNumbers")
    G = np.asarray(Gv.backend_buffer(), float).reshape(-1)
    ok = ~np.isnan(G)
    if np.any(G[ok] < 1) or np.any(G[ok] != np.round(G[ok])):
        raise _err("splitapply: the group numbers must be positive integers (see findgroups).",
                   "MATLAB:splitapply:InvalidGroupNumbers")
    ng = int(G[ok].max()) if ok.any() else 0
    present = set(int(x) for x in G[ok])
    if present != set(range(1, ng + 1)):
        raise _err("splitapply: every group number from 1 to max(G) must occur at least once.",
                   "MATLAB:splitapply:MissingGroupNums")
    data = []
    for X in args[1:-1]:
        if _is_table(X):
            data += list(X.cols)
        else:
            if hasattr(X, "shape") and len(X.shape) == 2 and X.shape[0] == 1 and X.shape[1] > 1 and not is_text(X):
                X = _transpose(X)
            data.append(X)
    for X in data:
        if height_of(X) != G.size:
            raise _err("splitapply: the data and the group numbers must have the same number of rows.",
                       "MATLAB:splitapply:InvalidSize")
    nout = max(1, nargout)
    results = []
    for g in range(1, ng + 1):
        rows = np.flatnonzero(G == g)
        out = fh.call([_col_rows(X, rows) for X in data], nargout=nout)
        if len(out) < nout:
            raise _err("splitapply: the function returned too few outputs.", "MATLAB:splitapply:TooFewOutputs")
        for v in out[:nout]:
            if not _is_table(v) and height_of(v) != 1:
                raise _err("splitapply: the function must return one row per group; wrap non-scalar results in a cell "
                           "with @(x) {f(x)}.", "MATLAB:splitapply:OutputNotScalar")
        results.append(list(out[:nout]))
    if not results:
        return tuple(NDArrayValue(np.zeros((0, 1))) for _ in range(nout))
    return tuple(_stack_split([r[k] for r in results]) for k in range(nout))


def _stack_split(vals):
    """Stack one output across groups. A table may have several rows; an array must already be one row."""
    tables = [_is_table(v) for v in vals]
    if any(tables) and not all(tables):
        raise _err("splitapply: the function must return a table for every group, or for none.",
                   "MATLAB:splitapply:OutputType")
    try:
        return _ev().concat_values([[v] for v in vals])
    except Exception as exc:
        if type(exc).__name__ == "EvalError":
            raise
        raise _err("splitapply: the function's outputs could not be concatenated.",
                   "MATLAB:splitapply:OutputType") from None


_METHODS = ("mean", "sum", "min", "max", "median", "mode", "var", "std", "range", "nnz", "numunique", "nummissing")


def _apply_method(m, a):
    a = np.asarray(a, float).reshape(-1)
    ok = a[~np.isnan(a)]
    if m == "nummissing":
        return float(np.isnan(a).sum())
    if m == "nnz":
        return float(np.count_nonzero(ok))
    if m == "numunique":
        return float(len(np.unique(ok)))
    if not ok.size:
        return 0.0 if m == "sum" else np.nan
    return float({"mean": np.mean, "sum": np.sum, "min": np.min, "max": np.max, "median": np.median,
                  "var": lambda x: np.var(x, ddof=1) if x.size > 1 else 0.0,
                  "std": lambda x: np.std(x, ddof=1) if x.size > 1 else 0.0,
                  "range": lambda x: np.max(x) - np.min(x),
                  "mode": lambda x: _mode(x)}[m](ok))


def _mode(x):
    vals, counts = np.unique(x, return_counts=True)
    return vals[np.argmax(counts)]


def _numeric_data(c, name, fn):
    if getattr(c, "is_object", False) or is_text(c) or getattr(c, "is_string", False) or not hasattr(c, "backend_buffer"):
        raise _err(f"{fn}: the method requires numeric or logical data; variable '{name}' is "
                   f"{c.matlab_class()}.", f"MATLAB:{fn}:InvalidDataVariable")
    return np.asarray(c.backend_buffer()).astype(float)


_FLAG_LABEL = {"includemissinggroups": "IncludeMissingGroups", "includeemptygroups": "IncludeEmptyGroups",
               "keepkeys": "KeepKeys", "includemissing": "IncludeMissing", "replacevalues": "ReplaceValues"}


def _flag(opts, key, default, fn):
    """Name-value logical. Absent returns ``default``. Anything other than scalar 0/1 is an error."""
    if key not in opts:
        return default
    v = opts[key]
    label = _FLAG_LABEL[key]
    if is_text(v) or getattr(v, "is_object", False) or not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: '{label}' must be 1 (true) or 0 (false).", f"MATLAB:{fn}:InvalidOption")
    a = np.asarray(v.backend_buffer()).reshape(-1)
    if a.size != 1 or np.iscomplexobj(a):
        raise _err(f"{fn}: '{label}' must be 1 (true) or 0 (false).", f"MATLAB:{fn}:InvalidOption")
    if a.dtype == np.bool_:
        return bool(a[0])
    if np.issubdtype(a.dtype, np.number):
        x = float(a[0])
        if x == 0.0 or x == 1.0:
            return bool(x)
    raise _err(f"{fn}: '{label}' must be 1 (true) or 0 (false).", f"MATLAB:{fn}:InvalidOption")


def _is_logical_col(col):
    return hasattr(col, "backend_buffer") and not getattr(col, "is_object", False) \
        and np.asarray(col.backend_buffer()).dtype == np.bool_


def _var_rank_list(col, n, ranker):
    """One rank vector per column of a grouping variable. A 0-row variable keeps its width."""
    if n == 0 and getattr(col, "is_categorical", False):
        width = col.codes.shape[1] if col.codes.ndim == 2 else 1
        return [np.zeros(0) for _ in range(max(int(width), 1))]
    one = list(ranker(col, n))
    if one:
        return one
    if n == 0:
        sh = getattr(col, "shape", (0, 1))
        width = int(sh[1]) if len(sh) > 1 else 1
        if width <= 0:
            return []
        return [np.zeros(0) for _ in range(width)]
    return one


def _var_levels(col, ranks, n):
    """Possible non-missing values of one grouping variable, as ``(rank tuple, one row)``.

    A column vector uses the closed domain when it has one: every categorical category, or both
    logical values. A wider variable is a single row-key, so only rows that actually occur are
    possible. Missing rows are not levels; the caller adds them from the data.
    """
    width = len(ranks)
    if width <= 1 and getattr(col, "is_categorical", False):
        return [(tuple([float(code)]), col.like(np.array([[code]], dtype=np.int64)))
                for code in range(1, len(col.cats) + 1)]
    if width <= 1 and _is_logical_col(col):
        return [(tuple([float(val)]), NDArrayValue(np.array([[val]], dtype=bool))) for val in (False, True)]
    if n == 0 or width == 0:
        return []
    R = np.column_stack(ranks)
    out, seen = [], set()
    for i in range(n):
        if np.any(np.isnan(R[i])):
            continue
        key = tuple(float(x) for x in R[i])
        if key in seen:
            continue
        seen.add(key)
        out.append((key, _col_rows(col, np.array([i]))))
    return out


def _stack_rows(parts, col):
    if not parts:
        return _col_rows(col, np.zeros(0, dtype=int))
    if len(parts) == 1:
        return parts[0]
    return _ev().concat_values([[p] for p in parts])


def _nan_last(key):
    """Sort key: a missing rank sorts after every real value in that column."""
    return tuple(np.inf if np.isnan(x) else float(x) for x in key)


def _groups_including_empty(cols, n, include_missing, ranker=_grouping_ranks):
    """Observed groups plus empty ones, in the same order as the default path.

    Sort column by column. A missing value sorts last inside its own column, so a
    group that contains a missing key stays where the default sort puts it. Empty
    combinations are inserted into that sequence. ``ranker`` must be the same
    function ``group_numbers`` uses, or a missing cellstr key and its sort key diverge.
    A multi-column variable contributes one factor: its row, not a product of its columns.
    """
    if not cols:
        # product() of no variables yields one empty tuple, which is not a group.
        G, firsts = group_numbers(cols, n, include_missing, ranker)
        return G, firsts, [], np.array([np.sum(G == g + 1) for g in range(len(firsts))], float)
    rank_lists = [_var_rank_list(col, n, ranker) for col in cols]
    levels = [_var_levels(col, ranks, n) for col, ranks in zip(cols, rank_lists)]
    combos = list(itertools.product(*levels)) if levels and all(levels) else []
    items, seen = [], set()
    Gobs = np.full(n, np.nan)
    if n:
        Gobs, firsts = group_numbers(cols, n, include_missing, ranker)
        flat = [r for ranks in rank_lists for r in ranks]
        R = np.column_stack(flat) if flat else np.zeros((n, 0))
        for fi in firsts:
            fi = int(fi)
            key = tuple(float(R[fi, j]) for j in range(R.shape[1]))
            parts = tuple(_col_rows(col, np.array([fi])) for col in cols)
            items.append((key, parts, float(Gobs[fi])))
            if not any(np.isnan(x) for x in key):
                seen.add(key)
    for combo in combos:
        key = tuple(x for level_key, _row in combo for x in level_key)
        if key in seen:
            continue
        items.append((key, tuple(row for _key, row in combo), None))
    items.sort(key=lambda it: _nan_last(it[0]))
    slot = {gobs: i for i, (_key, _parts, gobs) in enumerate(items) if gobs is not None}
    G = np.full(n, np.nan)
    for i in range(n):
        g = Gobs[i]
        if not np.isnan(g):
            G[i] = slot[float(g)] + 1
    keycols = [_stack_rows([it[1][j] for it in items], col) for j, col in enumerate(cols)]
    counts = np.array([np.sum(G == g + 1) for g in range(len(items))], float)
    return G, np.arange(len(items)), keycols, counts


def _group_table(T, gvars, fn, opts, *, allow_empty=False):
    include_missing = _flag(opts, "includemissinggroups", True, fn)
    include_empty = _flag(opts, "includeemptygroups", False, fn)
    if include_empty and not allow_empty:
        raise _err(f"{fn}: 'IncludeEmptyGroups' is not supported yet.", f"MATLAB:{fn}:Unsupported")
    cols = [T.cols[i] for i in gvars]
    # groupsummary and groupcounts. findgroups calls group_numbers on its own.
    if include_empty:
        return _groups_including_empty(cols, T.nrows, include_missing, _grouping_ranks)
    G, firsts = group_numbers(cols, T.nrows, include_missing, _grouping_ranks)
    keycols = [_col_rows(c, firsts) for c in cols]
    counts = np.array([np.sum(G == g + 1) for g in range(len(firsts))], float)
    return G, firsts, keycols, counts


_BIN_NAMES = frozenset((
    "none", "second", "minute", "hour", "day", "week", "month", "quarter", "year", "decade", "century",
    "secondofminute", "minuteofhour", "hourofday", "dayofweek", "dayname", "dayofmonth", "dayofyear",
    "weekofmonth", "weekofyear", "monthname", "monthofyear", "quarterofyear",
))
# Schemes whose category labels are fixed by the public groupsummary table.
_TIME_CATEGORICAL = frozenset((
    "dayname", "monthname", "secondofminute", "minuteofhour", "hourofday", "dayofweek",
    "dayofmonth", "dayofyear", "monthofyear", "quarterofyear",
))
_DAYNAMES = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
_MONTHNAMES = ("January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December")


def _cell_items(v):
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(v, CellValue):
        return [x for r in v.rows for x in r]
    return None


def _is_method_spec(v):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if isinstance(v, FunctionHandleValue):
        return True
    items = _cell_items(v)
    if items is not None:
        return bool(items) and all(_is_method_spec(x) for x in items)
    t = texts(v)
    return t is not None and all(s.lower() == "all" or s.lower() in _METHODS for s in t)


def _is_bin_spec(v):
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    if _is_method_spec(v):
        return False
    items = _cell_items(v)
    if items is not None:
        return bool(items) and all(_is_bin_spec(x) for x in items)
    t = texts(v)
    if t is not None:
        return len(t) == 1 and t[0].lower() in _BIN_NAMES
    from openmatlab.runtime.calendar_duration import CalendarDurationValue

    if isinstance(v, (DatetimeValue, DurationValue, CalendarDurationValue)):
        return True
    if getattr(v, "is_object", False) or is_text(v) or getattr(v, "is_string", False) or not hasattr(v, "backend_buffer"):
        return False
    a = np.asarray(v.backend_buffer())
    return a.dtype != np.bool_ and not np.iscomplexobj(a)


def _parse_methods(m):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if m is None:
        return []
    items = _cell_items(m)
    items = items if items is not None else [m]
    methods = []
    for it in items:
        if isinstance(it, FunctionHandleValue):
            methods.append(it)
            continue
        t = texts(it)
        if t is None:
            raise _err("groupsummary: methods must be names or function handles.", "MATLAB:groupsummary:InvalidMethod")
        for s in t:
            s = s.lower()
            if s == "all":
                methods += ["mean", "sum", "min", "max", "range", "median", "mode", "var", "std",
                            "nummissing", "nnz", "numunique"]
            elif s not in _METHODS:
                raise _err(f"groupsummary: '{s}' is not a valid method.", "MATLAB:groupsummary:InvalidMethod")
            else:
                methods.append(s)
    return methods


def _split_gs_args(data, is_table):
    rest = list(data[2:])
    bins = None
    if rest and _is_bin_spec(rest[0]):
        bins = rest.pop(0)
    methods = rest.pop(0) if rest else None
    datavars = None
    if rest:
        if not is_table:
            raise _err("groupsummary: array input does not take data-variable arguments.",
                       "MATLAB:groupsummary:TooManyInputs")
        datavars = rest.pop(0)
    if rest:
        raise _err("groupsummary: too many input arguments.", "MATLAB:TooManyInputs")
    if not is_table and methods is None:
        raise _err("groupsummary: array input requires a computation method.", "MATLAB:groupsummary:InvalidMethod")
    return bins, methods, datavars


def _included_edge(opts, has_bins, fn="groupsummary"):
    if "includededge" not in opts:
        return "left"
    if not has_bins:
        raise _err(f"{fn}: 'IncludedEdge' is only supported when group bins are specified.",
                   f"MATLAB:{fn}:IncludedEdge")
    t = texts(opts["includededge"])
    if t is None or len(t) != 1 or t[0].lower() not in ("left", "right"):
        raise _err(f"{fn}: 'IncludedEdge' must be 'left' or 'right'.", f"MATLAB:{fn}:IncludedEdge")
    return t[0].lower()


def _naming_rule(opts, is_table):
    if "variablenamingrule" not in opts:
        return "numbered"
    if not is_table:
        raise _err("groupsummary: 'VariableNamingRule' is only supported for table input.",
                   "MATLAB:groupsummary:VariableNamingRule")
    t = texts(opts["variablenamingrule"])
    if t is None or len(t) != 1 or t[0].lower() not in ("numbered", "methodname", "noprefix"):
        raise _err("groupsummary: 'VariableNamingRule' must be 'numbered', 'methodname', or 'noprefix'.",
                   "MATLAB:groupsummary:VariableNamingRule")
    return t[0].lower()


def _schemes_of(item):
    """One bin argument may itself be a cell of schemes for that one variable."""
    inner = _cell_items(item)
    return inner if inner is not None else [item]


def _expand_schemes(spec, nvars, fn="groupsummary"):
    """A list of schemes for each grouping variable.

    A scalar scheme applies to every variable. A cell with one entry per variable assigns
    each entry to that variable, and an entry that is itself a cell is several schemes for
    that variable (R2024a). One variable and a cell of schemes is that same case: every
    scheme applies to the variable. The public pages do not name an error id when the
    lengths disagree; this uses the project id ``MATLAB:<fn>:InvalidBins``.
    """
    if spec is None:
        return [[None]] * nvars
    items = _cell_items(spec)
    if items is None:
        return [[spec]] * nvars
    if len(items) == 1:
        return [_schemes_of(items[0])] * nvars
    if nvars == 1:
        return [items]
    if len(items) != nvars:
        raise _err(f"{fn}: the number of binning schemes must match the number of grouping variables, "
                   "or one of them must be scalar.",
                   f"MATLAB:{fn}:InvalidBins")
    return [_schemes_of(it) for it in items]


def _fmt_edge(x):
    x = float(x)
    if np.isnan(x):
        return "NaN"
    if np.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    if x == 0 or (abs(x) < 1e15 and x == int(x)):
        return str(int(x))
    return np.format_float_positional(x, trim="-")


def _interval_labels(edges, which):
    labels = []
    nb = len(edges) - 1
    for i in range(nb):
        a, b = _fmt_edge(edges[i]), _fmt_edge(edges[i + 1])
        if which == "left":
            labels.append(f"[{a}, {b}]" if i == nb - 1 else f"[{a}, {b})")
        else:
            labels.append(f"[{a}, {b}]" if i == 0 else f"({a}, {b}]")
    return labels


def _numeric_edges(v, fn="groupsummary"):
    a = np.asarray(v.backend_buffer(), float).reshape(-1)
    if a.size == 1:
        n = a[0]
        if not np.isfinite(n) or n != int(n) or n < 1:
            raise _err(f"{fn}: the number of bins must be a positive integer.", f"MATLAB:{fn}:InvalidBins")
        return ("count", int(n))
    if a.size < 2 or not np.all(np.isfinite(a)) or np.any(np.diff(a) <= 0):
        raise _err(f"{fn}: bin edges must be a finite, strictly increasing vector.", f"MATLAB:{fn}:InvalidBins")
    return ("edges", a)


def _equal_edges(x, nb, fn="groupsummary"):
    finite = np.asarray(x, float).reshape(-1)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        raise _err(f"{fn}: cannot bin a grouping variable that has no finite values.", f"MATLAB:{fn}:InvalidBins")
    lo, hi = float(finite.min()), float(finite.max())
    if lo == hi:
        lo, hi = lo - 0.5, hi + 0.5
    return np.linspace(lo, hi, nb + 1)


def _codes_for_edges(x, edges, which):
    flat = np.asarray(x, float).reshape(-1)
    nb = edges.size - 1
    if which == "left":
        idx = np.searchsorted(edges, flat, side="right") - 1
        on_end = flat == edges[-1]
        idx = np.where(on_end, nb - 1, idx)
    else:
        idx = np.searchsorted(edges, flat, side="left") - 1
        idx = np.where(flat == edges[0], 0, idx)
    bad = (~np.isfinite(flat)) | (idx < 0) | (idx >= nb)
    codes = np.zeros(flat.shape, dtype=np.int64)
    codes[~bad] = idx[~bad] + 1
    return codes.reshape(np.shape(np.asarray(x, float)))


def _bin_numeric(col, name, edges, which):
    from openmatlab.runtime.categorical_value import CategoricalValue

    x = np.asarray(col.backend_buffer(), float)
    if x.size == 0:
        x = np.zeros((height_of(col), _width(col, height_of(col)) or 1))
    codes = _codes_for_edges(x, edges, which)
    return CategoricalValue(codes, _interval_labels(edges, which), ordinal=True), "disc_" + name


def _time_codes(col, scheme):
    """Integer category codes (0 = missing) and the full category list for one time unit."""
    import datetime as _dt

    from openmatlab.runtime.objects import parts_from_datenum

    v = np.asarray(col.v, float)
    flat = v.reshape(-1)
    if scheme == "dayname":
        cats = list(_DAYNAMES)
        wd = np.mod(np.floor(flat) - 2, 7) + 1
        raw = wd
        lo = 1
    elif scheme == "monthname":
        cats = list(_MONTHNAMES)
        raw = np.array([np.nan if np.isnan(x) else parts_from_datenum(x)[1] for x in flat], float)
        lo = 1
    elif scheme == "dayofyear":
        cats = [str(k) for k in range(1, 367)]

        def yday(x):
            if np.isnan(x):
                return np.nan
            y, mo, d = parts_from_datenum(x)[:3]
            return float(_dt.date(int(y), int(mo), int(d)).timetuple().tm_yday)

        raw = np.array([yday(x) for x in flat], float)
        lo = 1
    else:
        spec = {
            "hourofday": (0, 23, 3), "minuteofhour": (0, 59, 4), "secondofminute": (0, 59, 5),
            "dayofweek": (1, 7, None), "dayofmonth": (1, 31, 2), "monthofyear": (1, 12, 1),
            "quarterofyear": (1, 4, "q"),
        }[scheme]
        lo, hi, part = spec
        cats = [str(k) for k in range(lo, hi + 1)]
        if scheme == "dayofweek":
            raw = np.mod(np.floor(flat) - 2, 7) + 1
        else:
            raw = np.empty(flat.shape, float)
            for i, x in enumerate(flat):
                if np.isnan(x):
                    raw[i] = np.nan
                    continue
                p = parts_from_datenum(x)
                if part == "q":
                    raw[i] = (p[1] - 1) // 3 + 1
                elif part == 5:
                    raw[i] = np.floor(p[5])
                else:
                    raw[i] = p[part]
    codes = np.zeros(flat.shape, dtype=np.int64)
    ok = np.isfinite(raw)
    codes[ok] = (raw[ok] - lo + 1).astype(np.int64)
    return codes.reshape(v.shape), cats


# Calendar-width units from the groupsummary / discretize tables (read 2026-11-07).
# discretize caps a duration binning at 2**16 bins and widens the step past that.
_MAX_BINS = 65536
_CAL_WIDTH = ("second", "minute", "hour", "day", "week", "month", "quarter", "year", "decade", "century")
# A duration has no calendar. 'year' is the fixed year the discretize page names; the others are fixed lengths.
_YEAR_DAYS = 365.2425
_DURATION_WIDTH = {
    "second": 1.0 / 86400.0, "minute": 1.0 / 1440.0, "hour": 1.0 / 24.0, "day": 1.0, "year": _YEAR_DAYS,
}


def _bracket(a, b, i, nb, which):
    if which == "left":
        return f"[{a}, {b}]" if i == nb - 1 else f"[{a}, {b})"
    return f"[{a}, {b}]" if i == 0 else f"({a}, {b}]"


def _finite_time(col):
    flat = np.asarray(col.v, float).reshape(-1)
    return flat, flat[np.isfinite(flat)]


def _empty_time_bins(col, name):
    from openmatlab.runtime.categorical_value import CategoricalValue

    shape = np.asarray(col.v, float).shape
    return CategoricalValue(np.zeros(shape, dtype=np.int64), [], ordinal=True), name


def _categorical_bins(values, edges, labels, which):
    from openmatlab.runtime.categorical_value import CategoricalValue

    codes = _codes_for_edges(np.asarray(values, float), np.asarray(edges, float), which)
    return CategoricalValue(codes, labels, ordinal=True)


def _unit_start(dn, unit):
    from openmatlab.libs.datetime_arrays import _start
    from openmatlab.runtime.objects import datenum_from_parts, parts_from_datenum

    if unit == "decade":
        y = parts_from_datenum(dn)[0]
        return datenum_from_parts(y - (y % 10), 1, 1)
    if unit == "century":
        y = parts_from_datenum(dn)[0]
        return datenum_from_parts(y - (y % 100), 1, 1)
    return _start(dn, unit)


def _unit_add(dn, unit, n):
    from openmatlab.libs.datetime_arrays import _add

    if n == 0:
        return dn
    if unit == "decade":
        return _add(dn, "year", 10 * n)
    if unit == "century":
        return _add(dn, "year", 100 * n)
    return _add(dn, unit, n)


def _calendar_step(unit, left, hi):
    """How many natural bins to fuse so the result stays within ``_MAX_BINS``."""
    from openmatlab.runtime.objects import parts_from_datenum

    def month_index(dn):
        y, mo = parts_from_datenum(dn)[:2]
        return y * 12 + (mo - 1)

    span = hi - left
    if unit == "second":
        n = span * 86400.0
    elif unit == "minute":
        n = span * 1440.0
    elif unit == "hour":
        n = span * 24.0
    elif unit == "day":
        n = span
    elif unit == "week":
        n = span / 7.0
    elif unit == "month":
        n = month_index(hi) - month_index(left)
    elif unit == "quarter":
        n = (month_index(hi) - month_index(left)) / 3.0
    elif unit == "year":
        n = parts_from_datenum(hi)[0] - parts_from_datenum(left)[0]
    elif unit == "decade":
        n = (parts_from_datenum(hi)[0] - parts_from_datenum(left)[0]) / 10.0
    else:
        n = (parts_from_datenum(hi)[0] - parts_from_datenum(left)[0]) / 100.0
    n = max(1, int(math.ceil(n - 1e-9)) + 1)
    return max(1, int(math.ceil(n / _MAX_BINS)))


def _walk_edges(left, hi, advance, fn, step=1):
    """Edges from ``left`` through the first edge strictly after ``hi``.

    ``advance(origin, n)`` is the edge ``n`` widths after ``origin``, computed from that origin
    rather than from the previous edge. Repeated ``cursor + width`` drifts off a datetime or
    duration that was built in one step, and an exact boundary then falls in the next bin.
    If ``step`` still needs more than ``_MAX_BINS`` edges, it doubles, which is the larger width
    discretize uses past that cap.
    """
    step = max(1, int(step))
    origin = float(left)
    for _attempt in range(16):
        edges = [origin]
        covered = False
        for i in range(1, _MAX_BINS + 1):
            nxt = float(advance(origin, i * step))
            if not np.isfinite(nxt) or nxt <= edges[-1]:
                raise _err(f"{fn}: the bin width must move time forward.", f"MATLAB:{fn}:InvalidBins")
            edges.append(nxt)
            if nxt > hi:
                covered = True
                break
        if covered:
            return np.asarray(edges, float)
        step *= 2
    raise _err(f"{fn}: the bin width does not cover the grouping values.", f"MATLAB:{fn}:InvalidBins")


def _calendar_edge(origin, unit, n):
    """Boundary ``n`` units after ``origin``, in the same formula ``datetime`` uses.

    Hour, minute, and second edges are rebuilt from the clock time. Adding ``1/24`` onto the
    previous edge does not equal ``datetime(y, mo, d, h, mi, s)`` once the additions repeat.
    """
    n = int(n)
    if n == 0:
        return float(origin)
    if unit in ("year", "quarter", "month", "decade", "century", "week", "day"):
        return float(_unit_add(float(origin), unit, n))
    import datetime as _dt

    from openmatlab.runtime.objects import datenum_from_parts, parts_from_datenum

    y, mo, d, h, mi, s = parts_from_datenum(origin)
    if unit == "hour":
        extra, h = divmod(int(h) + n, 24)
        mi, sec = 0, 0
    elif unit == "minute":
        extra_h, mi = divmod(int(mi) + n, 60)
        extra, h = divmod(int(h) + extra_h, 24)
        sec = 0
    else:
        extra_m, sec = divmod(int(round(s)) + n, 60)
        extra_h, mi = divmod(int(mi) + extra_m, 60)
        extra, h = divmod(int(h) + extra_h, 24)
    day = _dt.date(int(y), int(mo), int(d)) + _dt.timedelta(days=int(extra))
    return datenum_from_parts(day.year, day.month, day.day, h, mi, sec)


def _point_label(edge, unit):
    from openmatlab.runtime.objects import java_format, parts_from_datenum

    y, mo = parts_from_datenum(edge)[:2]
    if unit == "year":
        return f"{y:04d}"
    if unit == "month":
        return java_format(edge, "MMM-yyyy")
    if unit == "quarter":
        return f"Q{(mo - 1) // 3 + 1} {y}"
    if unit == "day":
        return java_format(edge, "dd-MMM-yyyy")
    return java_format(edge, "dd-MMM-yyyy HH:mm:ss")


def _calendar_labels(edges, unit, which):
    """Category names from the discretize ``dur,'categorical'`` table."""
    from openmatlab.runtime.objects import java_format, parts_from_datenum

    nb = len(edges) - 1
    labels = []
    for i in range(nb):
        left, right = float(edges[i]), float(edges[i + 1])
        if unit == "week":
            # The published example labels a week by its first day and its last day.
            a = java_format(left, "dd-MMM-yyyy")
            b = java_format(right - 1.0, "dd-MMM-yyyy")
            labels.append(_bracket(a, b, i, nb, which))
        elif unit in ("decade", "century"):
            a = str(parts_from_datenum(left)[0])
            b = str(parts_from_datenum(right)[0])
            labels.append(_bracket(a, b, i, nb, which))
        else:
            labels.append(_point_label(left, unit))
    return labels


def _bin_datetime_unit(col, name, unit, which, fn):
    _flat, finite = _finite_time(col)
    if finite.size == 0:
        return _empty_time_bins(col, f"{unit}_{name}")
    lo, hi = float(finite.min()), float(finite.max())
    left = _unit_start(lo, unit)

    def advance(origin, n):
        return _calendar_edge(origin, unit, n)

    edges = _walk_edges(left, hi, advance, fn, _calendar_step(unit, left, hi))
    labels = _calendar_labels(edges, unit, which)
    return _categorical_bins(col.v, edges, labels, which), f"{unit}_{name}"


def _fixed_edges(lo, hi, width, fn):
    """Edges on multiples of ``width`` for a duration value.

    A duration is stored as ``n * unit``, so the edge is the same product ``(k0 + n) * width``.
    ``anchor + n * width`` is a different float once ``anchor`` is itself a rounded product.
    """
    if not np.isfinite(width) or width <= 0:
        raise _err(f"{fn}: the bin width must be a positive duration.", f"MATLAB:{fn}:InvalidBins")
    k0 = math.floor(lo / width + 1e-12)
    left = k0 * width
    if left > lo:
        k0 -= 1
        left = k0 * width
    span = max(0.0, hi - left)
    n = max(1, int(math.ceil(span / width - 1e-9)) + 1)
    step = max(1, int(math.ceil(n / _MAX_BINS)))

    def advance(origin, n):
        return (k0 + n) * width

    return _walk_edges(left, hi, advance, fn, step)


def _component_edges(lo, hi, width, fn):
    """Datetime edges for any duration width, built with ``datenum_from_parts``.

    A datetime is ``day + h/24 + mi/1440 + s/86400``. Adding ``n * width`` to a datenum is not
    that value, for a half-second width as well as for an hour. The width is carried as an exact
    rational number of seconds, then split into clock components. There is no whole-second gate
    and no day-offset fallback.
    """
    from fractions import Fraction

    from openmatlab.runtime.objects import datenum_from_parts, parts_from_datenum

    if not np.isfinite(width) or width <= 0:
        raise _err(f"{fn}: the bin width must be a positive duration.", f"MATLAB:{fn}:InvalidBins")
    width_s = Fraction(float(width) * 86400.0)
    if width_s <= 0:
        raise _err(f"{fn}: the bin width must move time forward.", f"MATLAB:{fn}:InvalidBins")

    def edge_at(k):
        total = width_s * int(k)
        day = int(total // 86400)
        sod = total - day * 86400
        whole = int(sod)
        frac = float(sod - whole)
        hh, rem = divmod(whole, 3600)
        mm, ss = divmod(rem, 60)
        y, mo, d = parts_from_datenum(float(day))[:3]
        return datenum_from_parts(y, mo, d, hh, mm, ss + frac)

    guess = int(math.floor(float(lo) * 86400.0 / float(width_s)))
    lo_k, hi_k = guess, guess
    # The guess uses day-offset division, which is not the component value. Expand until the
    # component edges bracket ``lo``, then take the greatest edge that is still <= ``lo``.
    for _step in range(64):
        if edge_at(lo_k) <= lo:
            break
        lo_k -= max(1, hi_k - lo_k + 1)
    else:
        raise _err(f"{fn}: the bin width does not cover the grouping values.", f"MATLAB:{fn}:InvalidBins")
    for _step in range(64):
        if edge_at(hi_k) > lo:
            break
        hi_k += max(1, hi_k - lo_k + 1)
    else:
        raise _err(f"{fn}: the bin width does not cover the grouping values.", f"MATLAB:{fn}:InvalidBins")
    while lo_k < hi_k:
        mid = (lo_k + hi_k + 1) // 2
        if edge_at(mid) <= lo:
            lo_k = mid
        else:
            hi_k = mid - 1
    k0 = lo_k
    span = max(float(width), float(hi) - float(lo))
    nwidths = max(1, int(math.ceil(span / float(width))) + 1)
    step = max(1, int(math.ceil(nwidths / _MAX_BINS)))

    def advance(origin, n):
        return edge_at(k0 + int(n))

    return _walk_edges(edge_at(k0), hi, advance, fn, step)


def _duration_text(days, fmt):
    from openmatlab.runtime.objects import DurationValue

    return DurationValue(np.array([[float(days)]]), fmt).display_text().strip()


def _bin_fixed_width(values, width, which, fmt_edge, fn):
    flat = np.asarray(values, float).reshape(-1)
    finite = flat[np.isfinite(flat)]
    if finite.size == 0:
        from openmatlab.runtime.categorical_value import CategoricalValue

        return CategoricalValue(np.zeros(np.asarray(values, float).shape, dtype=np.int64), [], ordinal=True)
    edges = _fixed_edges(float(finite.min()), float(finite.max()), width, fn)
    nb = len(edges) - 1
    labels = [_bracket(fmt_edge(edges[i]), fmt_edge(edges[i + 1]), i, nb, which) for i in range(nb)]
    return _categorical_bins(values, edges, labels, which)


def _cd_days(cd):
    """Fixed length of a calendar duration, using the 365.2425-day year from the discretize page."""
    m = float(np.asarray(cd.m, float).reshape(-1)[0])
    d = float(np.asarray(cd.d, float).reshape(-1)[0])
    t = float(np.asarray(cd.t, float).reshape(-1)[0])
    return m * (_YEAR_DAYS / 12.0) + d + t


def _require_scalar(v, fn, what):
    if v.numel() != 1:
        raise _err(f"{fn}: {what} must be a scalar.", f"MATLAB:{fn}:InvalidBins")


def _bin_duration_width(col, name, width, which, fn):
    from openmatlab.runtime.objects import DatetimeValue, DurationValue, default_datetime_format, java_format

    if isinstance(col, DatetimeValue):
        _flat, finite = _finite_time(col)
        if finite.size == 0:
            return _empty_time_bins(col, "disc_" + name)
        edges = _component_edges(float(finite.min()), float(finite.max()), width, fn)
        fmt = col.fmt or default_datetime_format(edges)
        nb = len(edges) - 1
        labels = [_bracket(java_format(float(edges[i]), fmt), java_format(float(edges[i + 1]), fmt), i, nb, which)
                  for i in range(nb)]
        return _categorical_bins(col.v, edges, labels, which), "disc_" + name
    if isinstance(col, DurationValue):
        binned = _bin_fixed_width(col.v, width, which, lambda z: _duration_text(z, col.fmt), fn)
        return binned, "disc_" + name
    raise _err(f"{fn}: a duration bin width requires a datetime or duration grouping variable.",
               f"MATLAB:{fn}:InvalidBins")


def _bin_calendar_width(col, name, cd, which, fn):
    """A calendarDuration width. On a datetime it steps by calendar addition from the earliest value.

    On a duration there is no calendar, so the width becomes the fixed length above (a calendar
    year is 365.2425 days, and a month is one twelfth of that). Month-end clamping is the
    calendar addition this project already uses; end-of-month is not preserved.
    """
    from openmatlab.runtime.calendar_duration import shift, CalendarDurationValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue, default_datetime_format, java_format

    _require_scalar(cd, fn, "a calendarDuration bin width")
    if isinstance(col, DurationValue):
        return _bin_duration_width(col, name, _cd_days(cd), which, fn)
    if not isinstance(col, DatetimeValue):
        raise _err(f"{fn}: a calendarDuration bin width requires a datetime or duration grouping variable.",
                   f"MATLAB:{fn}:InvalidBins")
    _flat, finite = _finite_time(col)
    if finite.size == 0:
        return _empty_time_bins(col, "disc_" + name)
    lo, hi = float(finite.min()), float(finite.max())

    def advance(cursor, step):
        stepped = CalendarDurationValue(cd.m * step, cd.d * step, cd.t * step)
        return float(np.asarray(shift(np.array([[cursor]]), stepped), float).reshape(-1)[0])

    probe = advance(lo, 1)
    step0 = 1
    if probe > lo:
        n = max(1, int(math.ceil((hi - lo) / (probe - lo) - 1e-9)) + 1)
        step0 = max(1, int(math.ceil(n / _MAX_BINS)))
    edges = _walk_edges(lo, hi, advance, fn, step0)
    fmt = col.fmt or default_datetime_format(edges)
    nb = len(edges) - 1
    labels = [_bracket(java_format(float(edges[i]), fmt), java_format(float(edges[i + 1]), fmt), i, nb, which)
              for i in range(nb)]
    return _categorical_bins(col.v, edges, labels, which), "disc_" + name


def _bin_datetime_edges(col, name, edges_dt, which, fn):
    from openmatlab.runtime.objects import DatetimeValue, default_datetime_format, java_format

    ev = np.asarray(edges_dt.v, float).reshape(-1)
    if ev.size < 2 or not np.all(np.isfinite(ev)) or np.any(np.diff(ev) <= 0):
        raise _err(f"{fn}: datetime bin edges must be a finite, strictly increasing vector.",
                   f"MATLAB:{fn}:InvalidBins")
    if not isinstance(col, DatetimeValue):
        raise _err(f"{fn}: datetime bin edges require a datetime grouping variable.", f"MATLAB:{fn}:InvalidBins")
    fmt = edges_dt.fmt or default_datetime_format(edges_dt.v)
    nb = ev.size - 1
    labels = [_bracket(java_format(float(ev[i]), fmt), java_format(float(ev[i + 1]), fmt), i, nb, which)
              for i in range(nb)]
    return _categorical_bins(col.v, ev, labels, which), "disc_" + name


def _apply_bin(col, name, scheme, which, fn="groupsummary"):
    """Return ``(binned column, output name)``. ``scheme`` None or ``'none'`` keeps the column."""
    from openmatlab.runtime.calendar_duration import CalendarDurationValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    if scheme is None:
        return col, name
    if isinstance(scheme, DatetimeValue):
        return _bin_datetime_edges(col, name, scheme, which, fn)
    if isinstance(scheme, CalendarDurationValue):
        return _bin_calendar_width(col, name, scheme, which, fn)
    if isinstance(scheme, DurationValue):
        _require_scalar(scheme, fn, "a duration bin width")
        width = float(np.asarray(scheme.v, float).reshape(-1)[0])
        return _bin_duration_width(col, name, width, which, fn)
    t = texts(scheme)
    if t is not None:
        key = t[0].lower()
        if key == "none":
            return col, name
        if key in _TIME_CATEGORICAL:
            if not isinstance(col, DatetimeValue):
                raise _err(f"{fn}: binning scheme '{key}' requires a datetime grouping variable.",
                           f"MATLAB:{fn}:InvalidBins")
            from openmatlab.runtime.categorical_value import CategoricalValue

            codes, cats = _time_codes(col, key)
            return CategoricalValue(codes, cats, ordinal=True), f"{key}_{name}"
        if key in _CAL_WIDTH:
            if isinstance(col, DatetimeValue):
                return _bin_datetime_unit(col, name, key, which, fn)
            if isinstance(col, DurationValue):
                if key not in _DURATION_WIDTH:
                    raise _err(f"{fn}: binning scheme '{key}' requires a datetime grouping variable.",
                               f"MATLAB:{fn}:InvalidBins")
                binned = _bin_fixed_width(col.v, _DURATION_WIDTH[key], which,
                                          lambda z: _duration_text(z, col.fmt), fn)
                return binned, f"{key}_{name}"
            raise _err(f"{fn}: binning scheme '{key}' requires a datetime or duration grouping variable.",
                       f"MATLAB:{fn}:InvalidBins")
        raise _err(f"{fn}: binning scheme '{key}' is not supported yet.", f"MATLAB:{fn}:Unsupported")
    kind, payload = _numeric_edges(scheme, fn)
    if isinstance(col, (DatetimeValue, DurationValue)) or getattr(col, "is_object", False) or is_text(col) \
            or not hasattr(col, "backend_buffer"):
        raise _err(f"{fn}: numeric bin edges require a numeric grouping variable.", f"MATLAB:{fn}:InvalidBins")
    if kind == "count":
        x = np.asarray(col.backend_buffer(), float)
        payload = _equal_edges(x, payload, fn)
    return _bin_numeric(col, name, payload, which)


def _take_col(v, j):
    from openmatlab.runtime.table_subs import ix
    from openmatlab.runtime.table_value import _idx_value

    return ix(_ev(), v, [None, _idx_value(np.array([j]))])


def _matrix_columns(v):
    """Columns of one array. A row vector is one column. Char stays one key per row."""
    if is_text(v):
        return [v]
    sh = getattr(v, "shape", None)
    if sh is not None and len(sh) == 2 and sh[0] == 1 and sh[1] > 1:
        v = _transpose(v)
    n = height_of(v)
    w = _width(v, n) if n else (int(v.shape[1]) if len(getattr(v, "shape", ())) > 1 else 1)
    if w <= 1:
        return [v]
    return [_take_col(v, j) for j in range(w)]


def _flatten_columns(v):
    items = _cell_items(v)
    if items is None:
        return _matrix_columns(v)
    out = []
    for it in items:
        out.extend(_matrix_columns(it))
    return out


def _method_nargout(fh):
    defn = getattr(fh.fn, "defn", None)
    if defn is None:
        return 1
    outs = [o for o in defn.outputs if o != "varargout"]
    if not outs or (defn.outputs and defn.outputs[-1] == "varargout"):
        return 1
    return max(1, len(outs))


def _method_nargin(fh):
    defn = getattr(fh.fn, "defn", None)
    if defn is not None:
        return len([i for i in defn.inputs if i != "varargin"])
    name = getattr(fh, "name", "") or ""
    if name.startswith("@("):
        end = name.find(")")
        if end > 2:
            return len([p for p in name[2:end].split(",") if p.strip()])
    return 1


def _fun_row(fh, slices):
    nout = _method_nargout(fh)
    outs = list(fh.call(slices, nargout=nout))
    if len(outs) < nout:
        raise _err("groupsummary: the function returned too few outputs.", "MATLAB:groupsummary:FunctionOutputSize")
    row = outs[0] if nout == 1 else _ev().concat_values([outs[:nout]])
    if height_of(row) != 1:
        raise _err("groupsummary: a function method must return one row per group.",
                   "MATLAB:groupsummary:FunctionOutputSize")
    return row


def _stack_group_rows(vals):
    from openmatlab.runtime.evaluator import EvalError

    if not vals:
        return NDArrayValue(np.zeros((0, 1)))
    try:
        return _ev().concat_values([[v] for v in vals])
    except EvalError:
        raise
    except (TypeError, ValueError):
        raise _err("groupsummary: a function method must return one row of the same width for every group.",
                   "MATLAB:groupsummary:FunctionOutputSize") from None


def _named_block(method, col, G, n_groups, nrows, label):
    buf = _numeric_data(col, label, "groupsummary")
    # reshape(0, -1) cannot infer a width; an empty column vector is one column.
    if nrows:
        a = buf.reshape(nrows, -1)
    else:
        a = np.zeros((0, buf.shape[1] if getattr(buf, "ndim", 1) == 2 else 1))
    width = a.shape[1]
    if n_groups:
        out = np.array([[_apply_method(method, a[G == g + 1, j]) for j in range(width)]
                        for g in range(n_groups)], float).reshape(n_groups, width)
    else:
        out = np.zeros((0, width))
    return NDArrayValue(out)


def _fun_block(fh, arg_cols, G, n_groups):
    vals = []
    for g in range(n_groups):
        rows = np.flatnonzero(G == g + 1)
        vals.append(_fun_row(fh, [_col_rows(c, rows) for c in arg_cols]))
    return _stack_group_rows(vals)


def _stat_name(method, var, fun_i, rule):
    if rule == "noprefix":
        return var
    if isinstance(method, str):
        return f"{method}_{var}"
    if rule == "methodname":
        from openmatlab.libs.function_intrinsics import _canonical

        return f"{_canonical(method.name)}_{var}"
    return f"fun{fun_i}_{var}"


def _fun_indexes(methods):
    out, k = [], 0
    for m in methods:
        if isinstance(m, str):
            out.append(None)
        else:
            k += 1
            out.append(k)
    return out


def _multi_arity(methods):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    multi = [m for m in methods if isinstance(m, FunctionHandleValue) and _method_nargin(m) > 1]
    if not multi:
        return 1
    if len(methods) != 1:
        raise _err("groupsummary: a function with multiple inputs must be the only method.",
                   "MATLAB:groupsummary:InvalidMethod")
    return _method_nargin(methods[0])


def _same_height(cols, n, what):
    for c in cols:
        if height_of(c) != n:
            raise _err(f"groupsummary: the {what} must have the same number of rows as the data.",
                       "MATLAB:groupsummary:InvalidSize")


def _summary_pairs(pairs, methods, G, n_groups, nrows, rule):
    """Variable-major summary columns: each data pair, then each method."""
    if rule == "noprefix" and len(methods) != 1:
        raise _err("groupsummary: 'VariableNamingRule','noprefix' requires exactly one computation method.",
                   "MATLAB:groupsummary:VariableNamingRule")
    from openmatlab.runtime.function_handle import FunctionHandleValue

    names, cols = [], []
    fun_i = _fun_indexes(methods)
    for arg_cols, var in pairs:
        for m, fi in zip(methods, fun_i):
            if isinstance(m, FunctionHandleValue):
                cols.append(_fun_block(m, arg_cols, G, n_groups))
            else:
                if len(arg_cols) != 1:
                    raise _err("groupsummary: a named method takes one data argument.",
                               "MATLAB:groupsummary:InvalidMethod")
                cols.append(_named_block(m, arg_cols[0], G, n_groups, nrows, var))
            names.append(_stat_name(m, var, fi, rule))
    return names, cols


def _pair_table(T, spec, arity):
    items = _cell_items(spec)
    if items is None or len(items) != arity:
        raise _err("groupsummary: a function with multiple inputs needs datavars as a cell array "
                   "with one selection per input.", "MATLAB:groupsummary:InvalidDataVars")
    sels = [T.var_sel(it) for it in items]
    widths = {len(s) for s in sels}
    if len(widths) != 1 or not widths or 0 in widths:
        raise _err("groupsummary: each datavars selection must name the same nonzero number of variables.",
                   "MATLAB:groupsummary:InvalidDataVars")
    n = len(sels[0])
    pairs = []
    for j in range(n):
        cols = [T.cols[s[j]] for s in sels]
        pairs.append((cols, "_".join(T.names[s[j]] for s in sels)))
    return pairs


def _table_pairs(T, gvars, datavars, methods):
    arity = _multi_arity(methods)
    if not methods:
        return []
    if arity > 1:
        if datavars is None:
            raise _err("groupsummary: a function with multiple inputs needs datavars as a cell array.",
                       "MATLAB:groupsummary:InvalidDataVars")
        return _pair_table(T, datavars, arity)
    idx = T.var_sel(datavars) if datavars is not None else [i for i in range(len(T.names)) if i not in gvars]
    return [([T.cols[i]], T.names[i]) for i in idx]


def _array_pairs(A, methods):
    arity = _multi_arity(methods)
    if arity == 1:
        cols = _flatten_columns(A)
        return [([c], f"Var{k + 1}") for k, c in enumerate(cols)]
    items = _cell_items(A)
    if items is None or len(items) != arity:
        raise _err("groupsummary: a function with multiple inputs needs the data as a cell array "
                   "with one array per input.", "MATLAB:groupsummary:InvalidInput")
    splits = [_matrix_columns(it) for it in items]
    widths = {len(s) for s in splits}
    if len(widths) != 1 or not widths or 0 in widths:
        raise _err("groupsummary: each data array must have the same nonzero number of columns.",
                   "MATLAB:groupsummary:InvalidInput")
    n = len(splits[0])
    return [([splits[a][j] for a in range(arity)], f"Var{j + 1}") for j in range(n)]


def _bin_columns(cols, names, bins, which, fn="groupsummary"):
    per_var = _expand_schemes(bins, len(cols), fn)
    out_c, out_n, taken = [], [], set()
    for c, n, schemes in zip(cols, names, per_var):
        for s in schemes:
            bc, bn = _apply_bin(c, n, s, which, fn)
            out_c.append(bc)
            out_n.append(_fresh(bn, taken))
    return out_c, out_n


def _groupsummary(args, *, nargout=1):
    data, opts = _opts(args, ("includemissinggroups", "includeemptygroups", "variablenamingrule", "includededge"),
                       "groupsummary")
    if len(data) < 2:
        raise _err("groupsummary: not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    is_table = _is_table(data[0])
    bins, method_v, datavars = _split_gs_args(data, is_table)
    which = _included_edge(opts, bins is not None)
    rule = _naming_rule(opts, is_table)
    methods = _parse_methods(method_v)
    if is_table:
        T = data[0]
        gvars = T.var_sel(data[1])
        gcols, gnames = _bin_columns([T.cols[i] for i in gvars], [T.names[i] for i in gvars], bins, which)
        GT = TableValue(gnames, gcols, T.nrows)
        G, firsts, keycols, counts = _group_table(GT, list(range(len(gnames))), "groupsummary", opts, allow_empty=True)
        pairs = _table_pairs(T, gvars, datavars, methods)
        snames, scols = _summary_pairs(pairs, methods, G, len(firsts), T.nrows, rule)
        return (TableValue(gnames + ["GroupCount"] + snames, keycols + [_num_col(counts)] + scols, len(firsts)),)
    pairs = _array_pairs(data[0], methods)
    data_cols = [c for cols, _name in pairs for c in cols]
    if not data_cols:
        raise _err("groupsummary: the data input is empty.", "MATLAB:groupsummary:InvalidInput")
    n = height_of(data_cols[0])
    _same_height(data_cols, n, "data")
    gcols = _flatten_columns(data[1])
    if not gcols:
        raise _err("groupsummary: grouping variables are required.", "MATLAB:groupsummary:InvalidInput")
    _same_height(gcols, n, "grouping variables")
    gcols, _gnames = _bin_columns(gcols, [f"g{i + 1}" for i in range(len(gcols))], bins, which)
    GT = TableValue([f"g{i + 1}" for i in range(len(gcols))], gcols, n)
    G, firsts, keycols, counts = _group_table(GT, list(range(len(gcols))), "groupsummary", opts, allow_empty=True)
    _snames, scols = _summary_pairs(pairs, methods, G, len(firsts), n, "numbered")
    B = _horz_summary(scols, len(firsts))
    outs = [B]
    if nargout >= 2:
        outs.append(keycols[0] if len(keycols) == 1 else _cell_row(keycols))
    if nargout >= 3:
        outs.append(_num_col(counts))
    return tuple(outs[:max(1, nargout)])


def _horz_summary(cols, n_groups):
    if not cols:
        return NDArrayValue(np.zeros((n_groups, 0)))
    if len(cols) == 1:
        return cols[0]
    return _ev().concat_values([cols])


def _cell_row(items):
    from openmatlab.runtime.cell_value import CellValue

    return CellValue(rows=(tuple(items),)) if items else CellValue(rows=())


def _group_rows(G):
    G = np.asarray(G, float).reshape(-1)
    finite = G[np.isfinite(G)]
    ng = int(finite.max()) if finite.size else 0
    return [np.flatnonzero(G == g + 1) for g in range(ng)]


def _percent(counts, nrows):
    if not nrows:
        return counts
    return counts / float(nrows) * 100.0


def _groupcounts(args, *, nargout=1):
    data, opts = _opts(args, ("includemissinggroups", "includeemptygroups", "includededge"), "groupcounts")
    if not data:
        raise _err("groupcounts: not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if _is_table(data[0]):
        return _groupcounts_table(data, opts)
    return _groupcounts_array(data, opts, nargout)


def _groupcounts_table(data, opts):
    if len(data) < 2 or len(data) > 3:
        raise _err("groupcounts: expected groupcounts(T, groupvars) or groupcounts(T, groupvars, groupbins).",
                   "MATLAB:groupcounts:InvalidInput")
    bins = data[2] if len(data) == 3 else None
    if bins is not None and not _is_bin_spec(bins):
        raise _err("groupcounts: group bins must be a binning scheme.", "MATLAB:groupcounts:InvalidBins")
    which = _included_edge(opts, bins is not None, "groupcounts")
    T = data[0]
    gvars = T.var_sel(data[1])
    gcols, gnames = _bin_columns([T.cols[i] for i in gvars], [T.names[i] for i in gvars], bins, which, "groupcounts")
    grouped = TableValue(gnames, gcols, T.nrows)
    _G, firsts, keycols, counts = _group_table(grouped, list(range(len(gnames))), "groupcounts", opts, allow_empty=True)
    pct = _percent(counts, T.nrows)
    return (TableValue(gnames + ["GroupCount", "Percent"], keycols + [_num_col(counts), _num_col(pct)], len(firsts)),)


def _groupcounts_array(data, opts, nargout):
    if len(data) > 2:
        raise _err("groupcounts: too many input arguments.", "MATLAB:TooManyInputs")
    bins = data[1] if len(data) == 2 else None
    if bins is not None and not _is_bin_spec(bins):
        raise _err("groupcounts: group bins must be a binning scheme.", "MATLAB:groupcounts:InvalidBins")
    which = _included_edge(opts, bins is not None, "groupcounts")
    gcols = _flatten_columns(data[0])
    if not gcols:
        raise _err("groupcounts: the input array is empty.", "MATLAB:groupcounts:InvalidInput")
    n = height_of(gcols[0])
    for c in gcols[1:]:
        if height_of(c) != n:
            raise _err("groupcounts: grouping vectors must have the same number of rows.",
                       "MATLAB:groupcounts:InvalidSize")
    labels = [f"g{i + 1}" for i in range(len(gcols))]
    gcols, _names = _bin_columns(gcols, labels, bins, which, "groupcounts")
    grouped = TableValue(labels, gcols, n)
    _G, firsts, keycols, counts = _group_table(grouped, list(range(len(gcols))), "groupcounts", opts, allow_empty=True)
    pct = _percent(counts, n)
    outs = [_num_col(counts)]
    if nargout >= 2:
        outs.append(keycols[0] if len(keycols) == 1 else _cell_row(keycols))
    if nargout >= 3:
        outs.append(_num_col(pct))
    return tuple(outs[:max(1, nargout)])


_XFORM = ("zscore", "norm", "meancenter", "rescale", "meanfill", "linearfill")


def _split_method_call(data, is_table, fn):
    """``(bins or None, method, datavars or None)`` after the data and the grouping spec."""
    if len(data) < 3:
        raise _err(f"{fn}: not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    rest = list(data[2:])
    bins = None
    if rest and _is_bin_spec(rest[0]):
        bins = rest.pop(0)
    if not rest:
        raise _err(f"{fn}: not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    method = rest.pop(0)
    datavars = None
    if rest:
        if not is_table:
            raise _err(f"{fn}: too many input arguments.", "MATLAB:TooManyInputs")
        datavars = rest.pop(0)
    if rest:
        raise _err(f"{fn}: too many input arguments.", "MATLAB:TooManyInputs")
    return bins, method, datavars


def _xform_method(v, fn):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if isinstance(v, FunctionHandleValue):
        return v
    t = texts(v)
    if t is not None and len(t) == 1 and t[0].lower() in _XFORM:
        return t[0].lower()
    raise _err(f"{fn}: method must be 'zscore', 'norm', 'meancenter', 'rescale', 'meanfill', "
               "'linearfill', or a function handle.", f"MATLAB:{fn}:InvalidMethod")


def _operand_vars(T, gvars, datavars, fn):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if isinstance(datavars, FunctionHandleValue):
        raise _err(f"{fn}: selecting variables with a function handle is not supported.",
                   f"MATLAB:{fn}:InvalidDataVars")
    if datavars is None:
        skip = set(gvars)
        return [i for i in range(len(T.names)) if i not in skip]
    return T.var_sel(datavars)


def _fresh(name, taken):
    if name not in taken:
        taken.add(name)
        return name
    k = 1
    while f"{name}_{k}" in taken:
        k += 1
    taken.add(f"{name}_{k}")
    return f"{name}_{k}"


def _prepare_groups(cols, names, n, bins, which, opts, fn):
    """Group numbers for every row, the full-height grouping columns, and bin columns to append."""
    gcols, gnames = _bin_columns(cols, names, bins, which, fn)
    grouped = TableValue(gnames, gcols, n)
    # Missing keys stay one group so a row-aligned result still has every input row.
    G, _firsts, _keys, _counts = _group_table(grouped, list(range(len(gcols))), fn, opts, allow_empty=False)
    # 'none' returns the original column. Every other scheme is a bin column to append.
    orig = {id(c) for c in cols}
    extra = [(bn, bc) for bc, bn in zip(gcols, gnames) if id(bc) not in orig]
    return G, gcols, extra


def _scale_columns(block, calc):
    block = np.asarray(block, float)
    if block.ndim == 1:
        block = block.reshape(-1, 1)
    out = np.full(block.shape, np.nan, float)
    for j in range(block.shape[1]):
        x = block[:, j]
        ok = np.isfinite(x)
        y = calc(x, ok)
        if y is not None:
            out[ok, j] = y
    return out


def _zscore_vals(x, ok):
    if int(ok.sum()) < 2:
        return None
    mu = float(x[ok].mean())
    sd = float(x[ok].std(ddof=1))
    if sd == 0.0:
        return None
    return (x[ok] - mu) / sd


def _norm_vals(x, ok):
    if not ok.any():
        return None
    nrm = float(np.linalg.norm(x[ok]))
    if nrm == 0.0:
        return None
    return x[ok] / nrm


def _center_vals(x, ok):
    if not ok.any():
        return None
    return x[ok] - float(x[ok].mean())


def _rescale_vals(x, ok):
    if not ok.any():
        return None
    lo, hi = float(x[ok].min()), float(x[ok].max())
    if lo == hi:
        return None
    return (x[ok] - lo) / (hi - lo)


def _meanfill_block(block):
    out = np.array(block, float, copy=True)
    if out.ndim == 1:
        out = out.reshape(-1, 1)
    for j in range(out.shape[1]):
        x = out[:, j]
        ok = np.isfinite(x)
        if ok.any():
            x[~ok] = float(x[ok].mean())
    return out


def _linearfill_block(block):
    """Interior linear interpolation. Leading and trailing missing values stay missing."""
    out = np.array(block, float, copy=True)
    if out.ndim == 1:
        out = out.reshape(-1, 1)
    idx = np.arange(out.shape[0])
    for j in range(out.shape[1]):
        x = out[:, j]
        ok = np.isfinite(x)
        if int(ok.sum()) >= 2 and (~ok).any():
            x[~ok] = np.interp(idx[~ok], idx[ok], x[ok], left=np.nan, right=np.nan)
    return out


_SCALE = {"zscore": _zscore_vals, "norm": _norm_vals, "meancenter": _center_vals, "rescale": _rescale_vals}


def _transform_block(method, block):
    if method in _SCALE:
        return _scale_columns(block, _SCALE[method])
    if method == "meanfill":
        return _meanfill_block(block)
    if method == "linearfill":
        return _linearfill_block(block)
    raise _err(f"grouptransform: method '{method}' is not supported.", "MATLAB:grouptransform:InvalidMethod")


def _named_transform(method, col, G, n, label, fn):
    buf = _numeric_data(col, label, fn)
    if n:
        a = np.asarray(buf, float).reshape(n, -1)
    else:
        width = buf.shape[1] if getattr(buf, "ndim", 1) == 2 else 1
        a = np.zeros((0, width))
    out = np.full(a.shape, np.nan, float)
    for idx in _group_rows(G):
        if idx.size == 0:
            continue
        out[idx] = _transform_block(method, a[idx])
    return NDArrayValue(out)


def _fit_rows(v, n, fn):
    if n == 0:
        return v if height_of(v) == 0 else _col_rows(v, np.zeros(0, dtype=int))
    h = height_of(v)
    if h == n:
        return v
    if h == 1:
        return _ev().concat_values([[v] for _ in range(n)])
    raise _err(f"{fn}: the function must return one row, or one row per group member.",
               f"MATLAB:{fn}:FunctionOutputSize")


def _fun_transform(fh, col, G, n, fn):
    if n == 0:
        return _fit_rows(fh.call([_col_rows(col, np.zeros(0, dtype=int))], nargout=1)[0], 0, fn)
    slots = [None] * n
    for idx in _group_rows(G):
        if idx.size == 0:
            continue
        piece = _fit_rows(fh.call([_col_rows(col, idx)], nargout=1)[0], int(idx.size), fn)
        for k, row in enumerate(idx):
            slots[int(row)] = _col_rows(piece, np.array([k]))
    if any(s is None for s in slots):
        raise _err(f"{fn}: a row was not part of any group.", f"MATLAB:{fn}:InvalidGroup")
    return _ev().concat_values([[s] for s in slots])


def _transform_column(method, col, G, n, label, fn):
    if isinstance(method, str):
        return _named_transform(method, col, G, n, label, fn)
    return _fun_transform(method, col, G, n, fn)


def _method_label(method):
    return method if isinstance(method, str) else "fun1"


def _same_n(cols, n, fn, what):
    for c in cols:
        if height_of(c) != n:
            raise _err(f"{fn}: the {what} must have the same number of rows as the data.",
                       f"MATLAB:{fn}:InvalidSize")


def _grouptransform(args, *, nargout=1):
    data, opts = _opts(args, ("includededge", "replacevalues"), "grouptransform")
    if not data:
        raise _err("grouptransform: not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if _is_table(data[0]):
        return _grouptransform_table(data, opts)
    return _grouptransform_array(data, opts, nargout)


def _grouptransform_table(data, opts):
    fn = "grouptransform"
    bins, method_v, datavars = _split_method_call(data, True, fn)
    method = _xform_method(method_v, fn)
    which = _included_edge(opts, bins is not None, fn)
    replace = _flag(opts, "replacevalues", True, fn)
    T = data[0]
    gvars = T.var_sel(data[1])
    G, _gfull, extra = _prepare_groups([T.cols[i] for i in gvars], [T.names[i] for i in gvars],
                                       T.nrows, bins, which, opts, fn)
    produced = {i: _transform_column(method, T.cols[i], G, T.nrows, T.names[i], fn)
                for i in _operand_vars(T, gvars, datavars, fn)}
    names, cols = list(T.names), list(T.cols)
    taken = set(names)
    if replace:
        for i, col in produced.items():
            cols[i] = col
    else:
        label = _method_label(method)
        for i, col in produced.items():
            names.append(_fresh(f"{label}_{T.names[i]}", taken))
            cols.append(col)
    for bname, bcol in extra:
        names.append(_fresh(bname, taken))
        cols.append(bcol)
    return (TableValue(names, cols, T.nrows, T.rownames, T.description),)


def _grouptransform_array(data, opts, nargout):
    fn = "grouptransform"
    if _cell_items(data[0]) is not None:
        raise _err(f"{fn}: the data input must be a vector or matrix.", f"MATLAB:{fn}:InvalidInput")
    bins, method_v, _datavars = _split_method_call(data, False, fn)
    method = _xform_method(method_v, fn)
    which = _included_edge(opts, bins is not None, fn)
    replace = _flag(opts, "replacevalues", True, fn)
    dcols = _matrix_columns(data[0])
    if not dcols:
        raise _err(f"{fn}: the data input is empty.", f"MATLAB:{fn}:InvalidInput")
    n = height_of(dcols[0])
    _same_n(dcols, n, fn, "data")
    gcols = _flatten_columns(data[1])
    if not gcols:
        raise _err(f"{fn}: grouping variables are required.", f"MATLAB:{fn}:InvalidInput")
    _same_n(gcols, n, fn, "grouping variables")
    G, gfull, _extra = _prepare_groups(gcols, [f"g{i + 1}" for i in range(len(gcols))], n, bins, which, opts, fn)
    transformed = [_transform_column(method, c, G, n, f"Var{k + 1}", fn) for k, c in enumerate(dcols)]
    pieces = transformed if replace else list(dcols) + transformed
    B = pieces[0] if len(pieces) == 1 else _ev().concat_values([pieces])
    outs = [B]
    if nargout >= 2:
        outs.append(gfull[0] if len(gfull) == 1 else _cell_row(gfull))
    return tuple(outs[:max(1, nargout)])


def _as_keep_mask(v, n, fn):
    if is_text(v) or getattr(v, "is_object", False) or not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: the filtering method must return a logical scalar or column vector.",
                   f"MATLAB:{fn}:InvalidMethodOutput")
    a = np.asarray(v.backend_buffer())
    if a.dtype != np.bool_ or (a.ndim == 2 and a.shape[0] > 1 and a.shape[1] > 1):
        raise _err(f"{fn}: the filtering method must return a logical scalar or column vector.",
                   f"MATLAB:{fn}:InvalidMethodOutput")
    flat = a.reshape(-1)
    if flat.size == 1:
        return np.full(n, bool(flat[0]))
    if flat.size != n:
        raise _err(f"{fn}: a logical vector from the filtering method must have one element per group row.",
                   f"MATLAB:{fn}:InvalidMethodOutput")
    return flat


def _filter_mask(fh, cols, G, n, fn):
    if not cols:
        raise _err(f"{fn}: the method needs a data variable.", f"MATLAB:{fn}:InvalidDataVars")
    keep = np.ones(n, dtype=bool)
    for col in cols:
        mask = np.zeros(n, dtype=bool)
        for idx in _group_rows(G):
            if idx.size == 0:
                continue
            out = fh.call([_col_rows(col, idx)], nargout=1)
            if not out:
                raise _err(f"{fn}: the filtering method returned no output.", f"MATLAB:{fn}:InvalidMethodOutput")
            mask[idx] = _as_keep_mask(out[0], int(idx.size), fn)
        keep &= mask
    return keep


def _groupfilter(args, *, nargout=1):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    data, opts = _opts(args, ("includededge",), "groupfilter")
    if not data:
        raise _err("groupfilter: not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    is_table = _is_table(data[0])
    bins, method, datavars = _split_method_call(data, is_table, "groupfilter")
    if not isinstance(method, FunctionHandleValue):
        raise _err("groupfilter: the filtering method must be a function handle.", "MATLAB:groupfilter:InvalidMethod")
    which = _included_edge(opts, bins is not None, "groupfilter")
    if is_table:
        return _groupfilter_table(data[0], data[1], bins, which, method, datavars, opts)
    return _groupfilter_array(data[0], data[1], bins, which, method, opts, nargout)


def _groupfilter_table(T, gspec, bins, which, fh, datavars, opts):
    fn = "groupfilter"
    gvars = T.var_sel(gspec)
    G, _gfull, extra = _prepare_groups([T.cols[i] for i in gvars], [T.names[i] for i in gvars],
                                       T.nrows, bins, which, opts, fn)
    keep = _filter_mask(fh, [T.cols[i] for i in _operand_vars(T, gvars, datavars, fn)], G, T.nrows, fn)
    names, cols = list(T.names), list(T.cols)
    taken = set(names)
    for bname, bcol in extra:
        names.append(_fresh(bname, taken))
        cols.append(bcol)
    out = TableValue(names, cols, T.nrows, T.rownames, T.description)
    return (out.take_rows(_ev(), np.flatnonzero(keep)),)


def _groupfilter_array(A, gspec, bins, which, fh, opts, nargout):
    fn = "groupfilter"
    if _cell_items(A) is not None:
        raise _err(f"{fn}: the data input must be a vector or matrix.", f"MATLAB:{fn}:InvalidInput")
    dcols = _matrix_columns(A)
    if not dcols:
        raise _err(f"{fn}: the data input is empty.", f"MATLAB:{fn}:InvalidInput")
    n = height_of(dcols[0])
    gcols = _flatten_columns(gspec)
    if not gcols:
        raise _err(f"{fn}: grouping variables are required.", f"MATLAB:{fn}:InvalidInput")
    _same_n(gcols, n, fn, "grouping variables")
    G, gfull, _extra = _prepare_groups(gcols, [f"g{i + 1}" for i in range(len(gcols))], n, bins, which, opts, fn)
    keep_idx = np.flatnonzero(_filter_mask(fh, dcols, G, n, fn))
    outs = [_col_rows(A, keep_idx)]
    if nargout >= 2:
        taken = [_col_rows(c, keep_idx) for c in gfull]
        outs.append(taken[0] if len(taken) == 1 else _cell_row(taken))
    return tuple(outs[:max(1, nargout)])


def register(builtins) -> None:
    if "join" in builtins:  # string join(str, delim) stays; tables dispatch here
        orig = builtins["join"]

        def join(args, *, nargout=1):
            if args and _is_table(args[0]):
                return _join(args, nargout=nargout)
            return orig(args, nargout=nargout)
        builtins["join"] = join
    else:
        builtins["join"] = _join
    builtins.update(innerjoin=_innerjoin, outerjoin=_outerjoin, findgroups=_findgroups,
                    splitapply=_splitapply, groupsummary=_groupsummary, groupcounts=_groupcounts,
                    grouptransform=_grouptransform, groupfilter=_groupfilter)
