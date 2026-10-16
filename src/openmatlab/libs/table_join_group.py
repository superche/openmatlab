"""Joins and grouping (M10 T-E6, #696).

``join``/``innerjoin``/``outerjoin`` match rows on key variables by typed per-row keys; outputs are
sorted by key (inner/outer) or keep the left table's order (join). Unmatched outer rows are filled
with each type's missing value (NaN, NaT, '', <missing>, <undefined>, 0 for integers, false for
logical). ``findgroups``/``splitapply``/``groupsummary``/``groupcounts`` number groups by the sorted
unique combinations of the grouping variables (rank keys from ``table_utils``).
"""

from __future__ import annotations

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


def _key_spec(A, B, opts, fn):
    if "keys" in opts and ("leftkeys" in opts or "rightkeys" in opts):
        raise _err(f"{fn}: specify 'Keys', or 'LeftKeys' and 'RightKeys', not both.", f"MATLAB:table:{fn}:ConflictingKeys")
    if "keys" in opts:
        lk = A.var_sel(opts["keys"])
        rk = [B.var_index(A.names[i]) for i in lk]
    elif "leftkeys" in opts or "rightkeys" in opts:
        if not ("leftkeys" in opts and "rightkeys" in opts):
            raise _err(f"{fn}: 'LeftKeys' and 'RightKeys' must be given together.", f"MATLAB:table:{fn}:MissingKeys")
        lk, rk = A.var_sel(opts["leftkeys"]), B.var_sel(opts["rightkeys"])
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


def _keys_as(T, idx, names):
    return TableValue(list(names), [T.cols[i] for i in idx], T.nrows)


def _match(A, B, lk, rk, fn):
    knames = [f"k{j}" for j in range(len(lk))]
    KA, KB = _keys_as(A, lk, knames), _keys_as(B, rk, knames)
    for j in range(len(lk)):
        if _row_key_kind(A.cols[lk[j]]) != _row_key_kind(B.cols[rk[j]]):
            raise _err(f"{fn}: the key variables '{A.names[lk[j]]}' and '{B.names[rk[j]]}' have incompatible types.",
                       f"MATLAB:table:{fn}:KeyTypeMismatch")
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


def _sorted_pairs(pairs, KA, KB):
    """Sort (ia, ib) pairs by their key values (MATLAB orders join output by key)."""
    if not pairs:
        return pairs
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
    sa = "_" + (an or "left")
    sb = "_" + (bn or "right")
    L, R = list(left), list(right)
    for i, n in enumerate(L):
        if n in R or n in rename_all:
            j = R.index(n) if n in R else None
            L[i] = n + sa
            if j is not None:
                R[j] = n + sb
    return L, R


def _vars_opt(T, opts, key, default):
    return T.var_sel(opts[key]) if key in opts else default


def _innerjoin(args, *, nargout=1):
    data, opts = _opts(args, ("keys", "leftkeys", "rightkeys", "leftvariables", "rightvariables"), "innerjoin")
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
    lv = _vars_opt(A, opts, "leftvariables", list(range(len(A.names))))
    rv = _vars_opt(B, opts, "rightvariables", [j for j in range(len(B.names)) if j not in rk])
    ia = np.array([p[0] for p in pairs], dtype=int)
    ib = np.array([p[1] for p in pairs], dtype=int)
    Ln, Rn = _suffix_names([A.names[i] for i in lv], [B.names[j] for j in rv], an, bn)
    cols = [take_filled(A.cols[i], A.nrows, ia) for i in lv] + [take_filled(B.cols[j], B.nrows, ib) for j in rv]
    out = TableValue(_unique_names(Ln + Rn), cols, len(pairs))
    return (out, _num_col(ia + 1), _num_col(ib + 1))[:max(1, nargout)]


def _outerjoin(args, *, nargout=1):
    data, opts = _opts(args, ("keys", "leftkeys", "rightkeys", "leftvariables", "rightvariables", "type", "mergekeys"),
                       "outerjoin")
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
    lv = _vars_opt(A, opts, "leftvariables", list(range(len(A.names))))
    rv = _vars_opt(B, opts, "rightvariables", list(range(len(B.names))))
    names, cols = [], []
    if merge:
        lv_nokey = [i for i in lv if i not in lk]
        rv_nokey = [j for j in rv if j not in rk]
        key_names = [A.names[i] if A.names[i] == B.names[j] else f"{A.names[i]}_{B.names[j]}" for i, j in zip(lk, rk)]
        key_cols = []
        for i, j in zip(lk, rk):
            from_a = take_filled(A.cols[i], A.nrows, ia)
            from_b = take_filled(B.cols[j], B.nrows, ib)
            need_b = np.flatnonzero(ia < 0)
            if need_b.size:
                from openmatlab.runtime.table_subs import ix_asgn
                from openmatlab.runtime.table_value import _idx_value

                sub = _col_rows(from_b, need_b)
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
    out = TableValue(_unique_names(names), cols, len(pairs))
    return (out, _num_col(np.where(ia < 0, 0, ia + 1)), _num_col(np.where(ib < 0, 0, ib + 1)))[:max(1, nargout)]


def _join(args, *, nargout=1):
    data, opts = _opts(args, ("keys", "leftkeys", "rightkeys", "leftvariables", "rightvariables", "keepkeys"), "join")
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
    lv = _vars_opt(A, opts, "leftvariables", list(range(len(A.names))))
    rv = _vars_opt(B, opts, "rightvariables", [j for j in range(len(B.names)) if j not in rk])
    Ln, Rn = _suffix_names([A.names[i] for i in lv], [B.names[j] for j in rv], an, bn)
    cols = [A.cols[i] for i in lv] + [take_filled(B.cols[j], B.nrows, ib) for j in rv]
    out = TableValue(_unique_names(Ln + Rn), cols, A.nrows, A.rownames)
    return (out, _num_col(ib + 1))[:max(1, nargout)]


# =====================================================================
# grouping
# =====================================================================
def group_numbers(cols, n, include_missing):
    """(G as float array with NaN for missing groups, first-row index per group in group order)."""
    keys = []
    for c in cols:
        keys += rank_columns(c, n)
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
    if not args:
        raise _err("findgroups: not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    first = args[0]
    like_row = (not _is_table(first) and hasattr(first, "shape") and len(first.shape) == 2 and first.shape[0] == 1
                and first.shape[1] > 1 and not is_text(first))
    cols = []
    for g in args:
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
    G, firsts = group_numbers(cols, n, include_missing=False)
    outs = [_orient(G, like_row)]
    if _is_table(first) and len(args) == 1:
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
            if height_of(v) != 1:
                raise _err("splitapply: the function must return one row per group; wrap non-scalar results in a cell "
                           "with @(x) {f(x)}.", "MATLAB:splitapply:OutputNotScalar")
        results.append(list(out[:nout]))
    if not results:
        return tuple(NDArrayValue(np.zeros((0, 1))) for _ in range(nout))
    return tuple(_ev().concat_values([[r[k]] for r in results]) for k in range(nout))


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


def _group_table(T, gvars, fn, opts):
    include_missing = True
    if "includemissinggroups" in opts:
        include_missing = bool(np.asarray(opts["includemissinggroups"].backend_buffer()).reshape(-1)[0])
    if "includeemptygroups" in opts and bool(np.asarray(opts["includeemptygroups"].backend_buffer()).reshape(-1)[0]):
        raise _err(f"{fn}: 'IncludeEmptyGroups' is not supported yet.", f"MATLAB:{fn}:Unsupported")
    G, firsts = group_numbers([T.cols[i] for i in gvars], T.nrows, include_missing)
    keycols = [_col_rows(T.cols[i], firsts) for i in gvars]
    counts = np.array([np.sum(G == g + 1) for g in range(len(firsts))], float)
    return G, firsts, keycols, counts


def _groupsummary(args, *, nargout=1):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    data, opts = _opts(args, ("includemissinggroups", "includeemptygroups"), "groupsummary")
    if len(data) < 2 or not _is_table(data[0]):
        raise _err("groupsummary: expected groupsummary(T, groupvars, method, datavars) with a table input.",
                   "MATLAB:groupsummary:InvalidInput")
    if len(data) > 4:
        raise _err("groupsummary: group bins are not supported yet.", "MATLAB:groupsummary:Unsupported")
    T = data[0]
    gvars = T.var_sel(data[1])
    methods = []
    if len(data) >= 3:
        m = data[2]
        items = []
        from openmatlab.runtime.cell_value import CellValue

        if isinstance(m, CellValue):
            items = [x for r in m.rows for x in r]
        else:
            items = [m]
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
                    methods += [x for x in ("mean", "sum", "min", "max", "range", "median", "mode", "var", "std",
                                            "nummissing", "nnz", "numunique")]
                elif s not in _METHODS:
                    raise _err(f"groupsummary: '{s}' is not a valid method.", "MATLAB:groupsummary:InvalidMethod")
                else:
                    methods.append(s)
    if len(data) >= 4:
        dvars = T.var_sel(data[3])
    else:
        dvars = [i for i in range(len(T.names)) if i not in gvars] if methods else []
    G, firsts, keycols, counts = _group_table(T, gvars, "groupsummary", opts)
    names = [T.names[i] for i in gvars] + ["GroupCount"]
    cols = keycols + [_num_col(counts)]
    nf = 0
    for d in dvars:
        for m in methods:
            if isinstance(m, FunctionHandleValue):
                nf += 1
                vals = []
                for g in range(len(firsts)):
                    rows = np.flatnonzero(G == g + 1)
                    r = m.call([_col_rows(T.cols[d], rows)], nargout=1)
                    if not r or height_of(r[0]) != 1:
                        raise _err("groupsummary: a function method must return one row per group.",
                                   "MATLAB:groupsummary:FunctionOutputSize")
                    vals.append(r[0])
                cols.append(_ev().concat_values([[v] for v in vals]) if vals else NDArrayValue(np.zeros((0, 1))))
                names.append(f"fun{nf if len([x for x in methods if not isinstance(x, str)]) > 1 else 1}_{T.names[d]}")
                continue
            a = _numeric_data(T.cols[d], T.names[d], "groupsummary").reshape(T.nrows, -1)
            out = np.array([[_apply_method(m, a[G == g + 1, j]) for j in range(a.shape[1])]
                            for g in range(len(firsts))], float).reshape(len(firsts), -1)
            cols.append(NDArrayValue(out))
            names.append(f"{m}_{T.names[d]}")
    return (TableValue(names, cols, len(firsts)),)


def _groupcounts(args, *, nargout=1):
    data, opts = _opts(args, ("includemissinggroups", "includeemptygroups"), "groupcounts")
    if len(data) != 2 or not _is_table(data[0]):
        raise _err("groupcounts: expected groupcounts(T, groupvars) with a table input.", "MATLAB:groupcounts:InvalidInput")
    T = data[0]
    gvars = T.var_sel(data[1])
    G, firsts, keycols, counts = _group_table(T, gvars, "groupcounts", opts)
    pct = counts / T.nrows * 100 if T.nrows else counts
    names = [T.names[i] for i in gvars] + ["GroupCount", "Percent"]
    return (TableValue(names, keycols + [_num_col(counts), _num_col(pct)], len(firsts)),)


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
                    splitapply=_splitapply, groupsummary=_groupsummary, groupcounts=_groupcounts)
