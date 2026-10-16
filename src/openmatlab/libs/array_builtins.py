"""Array builders, sets and sorting (Epic #535).

repmat, logspace, meshgrid/ndgrid, cell2mat/num2cell/iscellstr, rot90, tril/
triu/diag/blkdiag, sub2ind/ind2sub, isequaln; the set family union/intersect/
setdiff/setxor/ismember and unique over numeric, char and cellstr inputs
(sorted or 'stable', 'rows'), and sortrows (column spec, descending,
cellstr).
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _is_char(v):
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue) and not getattr(v, "is_string", False)


def _is_cell(v):
    from openmatlab.runtime.cell_value import CellValue

    return isinstance(v, CellValue)


def _txt(v):
    return v.text


def _flag_set(args):
    return {_txt(a).lower() for a in args if _is_char(a)}


def _arr(v, fn):
    if not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: expected a numeric argument", "MATLAB:invalidType")
    b = np.asarray(v.backend_buffer())
    return b.reshape(1, 1) if b.ndim == 0 else (b.reshape(1, -1) if b.ndim == 1 else b)


def _num(x):
    return NDArrayValue(np.asarray(x, dtype=float).reshape(1, 1) if np.ndim(x) == 0 else np.asarray(x, dtype=float))


def _col(idx):
    return NDArrayValue(np.asarray(idx, dtype=float).reshape(-1, 1) + 1.0)


def _codes(v):
    rows = list(v.rows)
    w = max([len(r) for r in rows] + [0])
    return np.array([[ord(c) for c in r.ljust(w)] for r in rows], dtype=float).reshape(len(rows), w)


def _from_codes(a):
    from openmatlab.runtime.char_value import CharValue

    a = np.atleast_2d(a)
    if a.size == 0:
        return CharValue("")
    return CharValue(rows=tuple("".join(chr(int(x)) for x in row) for row in a))


def _cell_grid(v):
    r, c = v.shape
    return [[v.get(i, j) for j in range(c)] for i in range(r)]


def _mk_cell(grid):
    from openmatlab.runtime.cell_value import CellValue

    if not grid or not grid[0]:
        return CellValue(rows=())
    return CellValue(rows=tuple(tuple(r) for r in grid))


# ----------------------------------------------------------------- builders
def _rep_counts(args, fn):
    if len(args) == 1:
        c = [int(x) for x in _arr(args[0], fn).reshape(-1)]
        return c if len(c) > 1 else [c[0], c[0]]
    return [int(_arr(a, fn).reshape(-1)[0]) for a in args]


def _repmat(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    reps = [max(0, r) for r in _rep_counts(args[1:], "repmat")]
    v = args[0]
    if _is_cell(v):
        if len(reps) > 2:
            raise _err("repmat: N-D cell replication is not supported", "MATLAB:repmat:unsupported")
        g = _cell_grid(v)
        g = [row * reps[1] for row in g] * reps[0]
        return (_mk_cell(g),)
    if getattr(v, "is_struct", False):
        from openmatlab.runtime.struct_value import StructValue

        r, c = v.shape[:2]
        grid = np.empty((r, c), dtype=object)
        for k, e in enumerate(v.elems):
            grid[k % r, k // r] = e
        t = np.tile(grid, reps[:2])
        return (StructValue(t.shape, v.fields, tuple(t.reshape(-1, order="F"))),)
    if _is_char(v):
        return (_from_codes(np.tile(_codes(v), reps[:2])),)
    b = _arr(v, "repmat")
    shp = list(b.shape) + [1] * (len(reps) - b.ndim)
    reps = reps + [1] * (len(shp) - len(reps))
    out = np.tile(b.reshape(shp), reps)
    return (NDArrayValue(out),)


def _logspace(args, *, nargout=1):
    a = float(_arr(args[0], "logspace").reshape(-1)[0])
    b = float(_arr(args[1], "logspace").reshape(-1)[0])
    n = int(_arr(args[2], "logspace").reshape(-1)[0]) if len(args) > 2 else 50
    if b == math.pi:  # MATLAB: logspace(a, pi) spans 10^a .. pi
        return (NDArrayValue(np.logspace(a, math.log10(math.pi), n).reshape(1, -1)),)
    return (NDArrayValue(np.logspace(a, b, n).reshape(1, -1)),)


def _grid(fn, indexing):
    def f(args, *, nargout=1):
        if not args:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        vecs = [_arr(a, fn).reshape(-1) for a in args]
        n = max(nargout, 1)
        if len(vecs) == 1:
            vecs = vecs * max(2, n)
        outs = np.meshgrid(*vecs[: max(len(vecs), n)], indexing=indexing)
        return tuple(NDArrayValue(o) for o in outs)
    return f


def _cell2mat(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue

    if len(args) != 1 or not _is_cell(args[0]):
        raise _err("cell2mat: input must be a cell array", "MATLAB:cell2mat:InputNotCell")
    g = _cell_grid(args[0])
    if not g:
        return (NDArrayValue(np.zeros((0, 0))),)
    flat = [x for row in g for x in row]
    if any(_is_cell(x) or getattr(x, "is_struct", False) for x in flat):
        raise _err("cell2mat: cells of cells or structs are not supported.", "MATLAB:cell2mat:UnsupportedCellContent")
    chars = all(_is_char(x) for x in flat)
    if not chars and any(_is_char(x) for x in flat):
        raise _err("cell2mat: all contents must be the same data type.", "MATLAB:cell2mat:MixedDataTypes")
    to = _codes if chars else (lambda x: _arr(x, "cell2mat"))
    try:
        rows = [np.hstack([to(x) for x in row]) for row in g]
        out = np.vstack(rows)
    except ValueError:
        raise _err("Dimensions of arrays being concatenated are not consistent.", "MATLAB:catenate:dimensionMismatch") from None
    return (_from_codes(out) if chars else NDArrayValue(out),)


def _num2cell(args, *, nargout=1):
    v = args[0]
    if _is_cell(v):
        return (v,)
    if _is_char(v):
        a = _codes(v)
        return (_mk_cell([[_from_codes(np.array([[x]])) for x in row] for row in a]),)
    b = _arr(v, "num2cell")
    if b.ndim > 2:
        raise _err("num2cell: N-D input is not supported", "MATLAB:num2cell:unsupported")
    return (_mk_cell([[NDArrayValue(np.array([[x]], dtype=b.dtype)) for x in row] for row in b]),)


def _mat2cell(args, *, nargout=1):
    """mat2cell(A, r, c[, ...]): split a 2-D array into blocks (#766)."""
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    v = args[0]
    if _is_cell(v):
        from openmatlab.runtime.cell_value import CellValue

        grid = v.to_obj()
        wrap = lambda b: CellValue.from_obj(b) if b.size else CellValue(rows=())
    elif _is_char(v):
        grid = _codes(v)
        wrap = _from_codes
    else:
        grid = _arr(v, "mat2cell")
        wrap = NDArrayValue
    if grid.ndim > 2 or len(args) > 3:
        trailing = [int(np.sum(_arr(a, "mat2cell"))) for a in args[3:]]
        if grid.ndim > 2 or any(t != 1 for t in trailing):
            raise _err("mat2cell: N-D input is not supported", "MATLAB:mat2cell:unsupported")
    m, n = grid.shape
    if grid.size == 0 and len(args) > 2:  # '' and [] are 0x0 here; accept any empty split (1x0 char, #766)
        want = (int(np.sum(_arr(args[1], "mat2cell"))), int(np.sum(_arr(args[2], "mat2cell"))))
        if want[0] * want[1] == 0:
            grid = grid.reshape(want)
            m, n = want

    def sizes(a, total, dim):
        d = [int(x) for x in _arr(a, "mat2cell").reshape(-1)]
        if any(x < 0 for x in d) or sum(d) != total:
            raise _err(f"Input arguments, D1 through D2, must sum to each dimension of the input matrix size, [{m} {n}].",
                       "MATLAB:mat2cell:DimensionMismatch")
        return d
    rs = sizes(args[1], m, 1)
    cs = sizes(args[2], n, 2) if len(args) > 2 else [n]
    out, r0 = [], 0
    for r in rs:
        row, c0 = [], 0
        for c in cs:
            row.append(wrap(np.ascontiguousarray(grid[r0:r0 + r, c0:c0 + c])))
            c0 += c
        out.append(row)
        r0 += r
    return (_mk_cell(out),)


def _iscellstr(args, *, nargout=1):
    v = args[0]
    ok = _is_cell(v) and all(_is_char(x) and len(x.rows) <= 1 for row in _cell_grid(v) for x in row)
    return (NDArrayValue(np.array([[ok]])),)


def _rot90(args, *, nargout=1):
    k = int(_arr(args[1], "rot90").reshape(-1)[0]) if len(args) > 1 else 1
    v = args[0]
    if _is_char(v):
        return (_from_codes(np.rot90(_codes(v), k)),)
    return (NDArrayValue(np.ascontiguousarray(np.rot90(_arr(v, "rot90"), k))),)


def _tri(fn, op):
    def f(args, *, nargout=1):
        k = int(_arr(args[1], fn).reshape(-1)[0]) if len(args) > 1 else 0
        b = _arr(args[0], fn)
        if b.ndim != 2:
            raise _err(f"{fn}: first argument must be 2-D", "MATLAB:tril:firstInputMustBe2D")
        return (NDArrayValue(op(b, k)),)
    return f


def _diag(args, *, nargout=1):
    b = _arr(args[0], "diag")
    k = int(_arr(args[1], "diag").reshape(-1)[0]) if len(args) > 1 else 0
    if b.ndim != 2:
        raise _err("diag: first input must be 2-D", "MATLAB:diag:firstInputMustBe2D")
    if 1 in b.shape:
        return (NDArrayValue(np.diag(b.reshape(-1), k)),)
    d = np.diagonal(b, k).copy()
    return (NDArrayValue(d.reshape(-1, 1)),)


def _blkdiag(args, *, nargout=1):
    mats = [_arr(a, "blkdiag") for a in args]
    r = sum(m.shape[0] for m in mats)
    c = sum(m.shape[1] for m in mats)
    dt = np.result_type(*mats) if mats else float
    out = np.zeros((r, c), dtype=dt)
    i = j = 0
    for m in mats:
        out[i:i + m.shape[0], j:j + m.shape[1]] = m
        i += m.shape[0]
        j += m.shape[1]
    return (NDArrayValue(out),)


def _sub2ind(args, *, nargout=1):
    sz = [int(x) for x in _arr(args[0], "sub2ind").reshape(-1)]
    subs = [_arr(a, "sub2ind").astype(float) for a in args[1:]]
    if not subs:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    shape = subs[0].shape
    if any(s.shape != shape for s in subs):
        raise _err("The subscript vectors must all be of the same size.", "MATLAB:sub2ind:SubscriptVectorSize")
    dims = sz + [1] * (len(subs) - len(sz))
    if len(subs) < len(dims):  # trailing dims fold into the last subscript
        dims = dims[: len(subs) - 1] + [int(np.prod(dims[len(subs) - 1:]))]
    ind = np.zeros(shape)
    mult = 1
    for s, d in zip(subs, dims):
        if np.any(s < 1) or np.any(s > d) or np.any(s != np.floor(s)):
            raise _err("Out of range subscript.", "MATLAB:sub2ind:IndexOutOfRange")
        ind = ind + (s - 1) * mult
        mult *= d
    return (NDArrayValue(ind + 1),)


def _ind2sub(args, *, nargout=1):
    sz = [int(x) for x in _arr(args[0], "ind2sub").reshape(-1)]
    ind = _arr(args[1], "ind2sub").astype(float)
    n = max(nargout, 1)
    total = int(np.prod(sz))
    if np.any(ind < 1) or np.any(ind > total) or np.any(ind != np.floor(ind)):
        raise _err("Index out of range; index must be a positive integer less than or equal to the number of elements.", "MATLAB:ind2sub:IndexOutOfRange")
    dims = sz + [1] * max(0, n - len(sz))
    if n < len(dims):
        dims = dims[: n - 1] + [int(np.prod(dims[n - 1:]))]
    rem = ind - 1
    outs = []
    for d in dims[:-1]:
        outs.append(NDArrayValue(np.mod(rem, d) + 1))
        rem = np.floor(rem / d)
    outs.append(NDArrayValue(rem + 1))
    return tuple(outs[:n])


def _isequaln(args, *, nargout=1):
    def eq(a, b):
        if _is_cell(a) and _is_cell(b):
            return a.shape == b.shape and all(eq(x, y) for x, y in zip(sum(_cell_grid(a), []), sum(_cell_grid(b), [])))
        if _is_char(a) or _is_char(b):
            return _is_char(a) and _is_char(b) and a.rows == b.rows
        if getattr(a, "is_struct", False) or getattr(b, "is_struct", False):
            return (getattr(a, "is_struct", False) and getattr(b, "is_struct", False) and a.shape == b.shape
                    and set(a.fields) == set(b.fields) and all(eq(x[f], y[f]) for x, y in zip(a.elems, b.elems) for f in a.fields))
        x, y = _arr(a, "isequaln"), _arr(b, "isequaln")
        if x.shape != y.shape:
            return False
        xf, yf = x.astype(complex), y.astype(complex)
        both_nan = np.isnan(xf) & np.isnan(yf)
        return bool(np.all((xf == yf) | both_nan))

    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    ok = all(eq(args[0], b) for b in args[1:])
    return (NDArrayValue(np.array([[ok]])),)


# ----------------------------------------------------------------- set engine
class _Set:
    """Elements of a set operand: kind 'num' | 'char' | 'cellstr'."""

    def __init__(self, v, fn):
        self.v = v
        if _is_cell(v):
            g = _cell_grid(v)
            flat = [g[i][j] for j in range(len(g[0]) if g else 0) for i in range(len(g))]
            if not all(_is_char(x) for x in flat):
                raise _err(f"{fn}: cell array inputs must be cell arrays of character vectors.", "MATLAB:" + fn + ":InputClass")
            self.kind, self.keys = "cellstr", [x.text for x in flat]
            self.shape = v.shape if g else (0, 0)
            self.dtype = None
        elif _is_char(v):
            a = _codes(v)
            self.kind, self.keys, self.shape, self.dtype = "char", a.reshape(-1, order="F").tolist(), a.shape, None
        else:
            a = _arr(v, fn)
            self.kind, self.shape, self.dtype = "num", a.shape, a.dtype
            self.keys = a.reshape(-1, order="F").tolist()

    def isrow(self):
        return len(self.shape) == 2 and self.shape[0] == 1

    def empty00(self):
        return tuple(self.shape) == (0, 0)


def _sortkey(k):
    if isinstance(k, str):
        return (0, k)
    if isinstance(k, complex):
        return (1 if math.isnan(abs(k)) else 0, abs(k), math.atan2(k.imag, k.real))
    return (1 if (isinstance(k, float) and math.isnan(k)) else 0, k)


def _common_kind(sets, fn):
    kinds = {s.kind for s in sets if not (s.empty00() and s.kind == "num")} or {"num"}
    if "cellstr" in kinds:
        for s in sets:
            if s.kind == "char":
                s.kind, s.keys = "cellstr", ["".join(chr(int(c)) for c in s.keys)] if s.keys else [""]
                s.shape = (1, 1)
            elif s.kind == "num" and s.empty00():
                s.kind, s.keys = "cellstr", []
        if any(s.kind != "cellstr" for s in sets):
            raise _err(f"{fn}: inputs must both be cell arrays of character vectors, or one may be a character vector.", f"MATLAB:{fn}:InputClass")
        return "cellstr"
    if "char" in kinds and all(s.kind in ("char", "num") for s in sets):
        return "char" if all(s.kind == "char" or s.empty00() for s in sets) else "num"
    return "num"


def _out_dtype(sets):
    dts = [s.dtype for s in sets if s.dtype is not None and not s.empty00()]
    ints = [d for d in dts if np.issubdtype(d, np.integer)]
    if ints:
        return ints[0]
    if any(d == np.float32 for d in dts):
        return np.float32
    if dts and all(d == bool for d in dts):
        return bool
    return np.complex128 if any(np.issubdtype(d, np.complexfloating) for d in dts) else np.float64


def _make(kind, keys, row, dtype):
    if kind == "cellstr":
        from openmatlab.runtime.char_value import CharValue

        if not keys:
            return _mk_cell([]) if not row else _mk_cell([[]])
        items = [CharValue(k) for k in keys]
        return _mk_cell([items] if row else [[x] for x in items])
    if kind == "char":
        a = np.array(keys, dtype=float)
        if a.size == 0:
            from openmatlab.runtime.char_value import CharValue

            return CharValue("")
        return _from_codes(a.reshape(1, -1) if row else a.reshape(-1, 1))
    a = np.array(keys, dtype=dtype if dtype is not None else float)
    if a.size == 0:
        return NDArrayValue(np.zeros((1, 0) if row else (0, 1), dtype=a.dtype))
    return NDArrayValue(a.reshape(1, -1) if row else a.reshape(-1, 1))


def _first_index(keys):
    first = {}
    for i, k in enumerate(keys):
        if k not in first or (isinstance(k, float) and math.isnan(k)):
            if isinstance(k, float) and math.isnan(k):
                first[("nan", i)] = i
            else:
                first[k] = i
    return first


def _last_index(keys):
    last = {}
    for i, k in enumerate(keys):
        last[k] = i
    return last


def _order(keys_idx, stable):
    """keys_idx: list of (key, index). Sorted by key or by first index (stable)."""
    if stable:
        return sorted(keys_idx, key=lambda t: t[1])
    return sorted(keys_idx, key=lambda t: _sortkey(t[0]))


def _opts(args, fn):
    flags = _flag_set(args)
    bad = flags - {"stable", "sorted", "rows", "first", "last", "legacy"}
    if bad:
        raise _err(f"{fn}: unknown option '{sorted(bad)[0]}'", f"MATLAB:{fn}:UnknownFlag")
    return flags


def _split(args, nsets, fn):
    data = list(args[:nsets])
    rest = list(args[nsets:])
    if len(data) < nsets:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if any(_is_char(a) and _txt(a).lower() in ("stable", "sorted", "rows", "first", "last", "legacy") for a in data[1:]) and nsets > 1 and False:
        pass
    return data, _opts(rest, fn)


def _rows_view(v, fn):
    a = _codes(v) if _is_char(v) else _arr(v, fn)
    return [tuple(r) for r in a.tolist()], a


def _rows_result(rows, ncols, like):
    a = np.array(rows, dtype=float).reshape(len(rows), ncols)
    if like is not None and np.issubdtype(like.dtype, np.integer):
        a = a.astype(like.dtype)
    return NDArrayValue(a)


def _unique(orig):
    def f(args, *, nargout=1):
        if not args:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        flags = _opts(args[1:], "unique")
        v = args[0]
        if not _is_cell(v) and not _is_char(v) and not (flags & {"stable", "last"}):
            return orig(args, nargout=nargout)
        if "rows" in flags:
            rows, a = _rows_view(v, "unique")
            idx = list(range(len(rows)))
            first = {}
            for i, r in enumerate(rows):
                if "last" in flags or r not in first:
                    first[r] = i
            pairs = _order([(r, first[r]) for r in first], "stable" in flags)
            C = [p[0] for p in pairs]
            pos = {r: k for k, r in enumerate(C)}
            out = _rows_result(C, a.shape[1], a) if not _is_char(v) else _from_codes(np.array(C).reshape(len(C), a.shape[1]))
            return (out, _col([p[1] for p in pairs]), _col([pos[r] for r in rows]))[: max(nargout, 1)]
        s = _Set(v, "unique")
        pick = _last_index(s.keys) if "last" in flags else {}
        if not pick:
            for i, k in enumerate(s.keys):
                if isinstance(k, float) and math.isnan(k):
                    pick[("nan", i)] = i
                elif k not in pick:
                    pick[k] = i
        pairs = _order([(s.keys[i], i) for i in pick.values()], "stable" in flags)
        keys = [p[0] for p in pairs]
        pos = {}
        for k_i, (k, i) in enumerate(pairs):
            pos.setdefault(k, k_i)
        ic = [pos.get(k, 0) for k in s.keys]
        row = s.isrow() and s.kind != "cellstr" or (s.kind == "cellstr" and s.isrow())
        C = _make(s.kind, keys, row, _out_dtype([s]))
        return (C, _col([p[1] for p in pairs]), _col(ic))[: max(nargout, 1)]
    return f


def _orient(sets):
    nonempty = [s for s in sets if not s.empty00()]
    return all(s.isrow() or (len(s.shape) == 2 and s.shape == (1, 1)) for s in nonempty) if nonempty else True


def _setop(fn):
    def f(args, *, nargout=1):
        data, flags = _split(args, 2, fn)
        if "rows" in flags:
            (ra, a), (rb, b) = _rows_view(data[0], fn), _rows_view(data[1], fn)
            return _setop_rows(fn, ra, rb, a, b, flags, nargout)
        A, B = _Set(data[0], fn), _Set(data[1], fn)
        kind = _common_kind([A, B], fn)
        stable = "stable" in flags
        fa = {}
        for i, k in enumerate(A.keys):
            fa.setdefault(k, i)
        fb = {}
        for i, k in enumerate(B.keys):
            fb.setdefault(k, i)
        if fn == "union":
            pa = [(k, i, 0) for k, i in fa.items()]
            pb = [(k, i, 1) for k, i in fb.items() if k not in fa]
            items = (sorted(pa, key=lambda t: t[1]) + sorted(pb, key=lambda t: t[1])) if stable else sorted(pa + pb, key=lambda t: _sortkey(t[0]))
            keys = [t[0] for t in items]
            ia = [t[1] for t in items if t[2] == 0]
            ib = [t[1] for t in items if t[2] == 1]
            outs = (keys, ia, ib)
        elif fn == "intersect":
            items = [(k, i) for k, i in fa.items() if k in fb]
            items = _order(items, stable)
            keys = [t[0] for t in items]
            outs = (keys, [t[1] for t in items], [fb[k] for k in keys])
        elif fn == "setdiff":
            items = _order([(k, i) for k, i in fa.items() if k not in fb], stable)
            keys = [t[0] for t in items]
            outs = (keys, [t[1] for t in items])
        else:  # setxor
            pa = [(k, i, 0) for k, i in fa.items() if k not in fb]
            pb = [(k, i, 1) for k, i in fb.items() if k not in fa]
            items = (sorted(pa, key=lambda t: t[1]) + sorted(pb, key=lambda t: t[1])) if stable else sorted(pa + pb, key=lambda t: _sortkey(t[0]))
            keys = [t[0] for t in items]
            outs = (keys, [t[1] for t in items if t[2] == 0], [t[1] for t in items if t[2] == 1])
        row = _orient([A, B]) if fn != "setdiff" else (A.isrow() or A.empty00() or tuple(A.shape) == (1, 1))
        C = _make(kind, outs[0], row, _out_dtype([A, B]) if kind == "num" else None)
        res = (C,) + tuple(_col(x) for x in outs[1:])
        return res[: max(nargout, 1)]
    return f


def _setop_rows(fn, ra, rb, a, b, flags, nargout):
    stable = "stable" in flags
    fa, fb = {}, {}
    for i, r in enumerate(ra):
        fa.setdefault(r, i)
    for i, r in enumerate(rb):
        fb.setdefault(r, i)
    if fn == "union":
        items = [(r, i, 0) for r, i in fa.items()] + [(r, i, 1) for r, i in fb.items() if r not in fa]
    elif fn == "intersect":
        items = [(r, i, 0) for r, i in fa.items() if r in fb]
    elif fn == "setdiff":
        items = [(r, i, 0) for r, i in fa.items() if r not in fb]
    else:
        items = [(r, i, 0) for r, i in fa.items() if r not in fb] + [(r, i, 1) for r, i in fb.items() if r not in fa]
    items = sorted(items, key=lambda t: (t[2], t[1])) if stable else sorted(items, key=lambda t: t[0])
    rows = [t[0] for t in items]
    ncols = a.shape[1] if a.size else b.shape[1]
    C = _rows_result(rows, ncols, a)
    if fn == "intersect":
        return (C, _col([t[1] for t in items]), _col([fb[t[0]] for t in items]))[: max(nargout, 1)]
    return (C, _col([t[1] for t in items if t[2] == 0]), _col([t[1] for t in items if t[2] == 1]))[: max(nargout, 1)]


def _ismember(args, *, nargout=1):
    data, flags = _split(args, 2, "ismember")
    if "rows" in flags:
        (ra, a), (rb, b) = _rows_view(data[0], "ismember"), _rows_view(data[1], "ismember")
        first = {}
        for i, r in enumerate(rb):
            first.setdefault(r, i)
        tf = [r in first for r in ra]
        loc = [first.get(r, -1) + 1 for r in ra]
        return (NDArrayValue(np.array(tf).reshape(-1, 1)), NDArrayValue(np.array(loc, float).reshape(-1, 1)))[: max(nargout, 1)]
    A, B = _Set(data[0], "ismember"), _Set(data[1], "ismember")
    if A.kind == "char" and B.kind == "cellstr":  # ismember('b', {'a','b'}): whole char vector
        A.kind, A.keys, A.shape = "cellstr", ["".join(chr(int(c)) for c in A.keys)], (1, 1)
    _common_kind([A, B], "ismember")
    first = {}
    for i, k in enumerate(B.keys):
        first.setdefault(k, i)
    tf = np.array([k in first for k in A.keys], dtype=bool)
    loc = np.array([first.get(k, -1) + 1 for k in A.keys], dtype=float)
    shape = A.shape if A.kind != "cellstr" else (A.shape if A.keys else (0, 0))
    if A.kind == "cellstr" and isinstance(data[0], type(data[0])) and not _is_cell(data[0]):
        shape = (1, 1)
    tf = tf.reshape(shape, order="F") if tf.size else np.zeros(shape, bool)
    loc = loc.reshape(shape, order="F") if loc.size else np.zeros(shape)
    return (NDArrayValue(tf), NDArrayValue(loc))[: max(nargout, 1)]


# ----------------------------------------------------------------- sortrows
def _sortrows(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    v = args[0]
    spec = None
    desc_all = False
    for a in args[1:]:
        if _is_char(a):
            w = _txt(a).lower()
            if w == "descend":
                desc_all = True
            elif w != "ascend":
                raise _err(f"sortrows: unknown option '{w}'", "MATLAB:sortrows:unknownOption")
        else:
            spec = [int(x) for x in _arr(a, "sortrows").reshape(-1)]
    if _is_cell(v):
        g = _cell_grid(v)
        if not g:
            return (v, NDArrayValue(np.zeros((0, 1))))[: max(nargout, 1)]
        ncol = len(g[0])
        cols = spec or list(range(1, ncol + 1))
        idx = list(range(len(g)))
        for c in reversed(cols):
            k = abs(c) - 1
            if not all(_is_char(r[k]) for r in g):
                raise _err("sortrows: only cell arrays of character vectors are supported.", "MATLAB:sortrows:cellNotCellstr")
            idx.sort(key=lambda i: g[i][k].text, reverse=(c < 0) != desc_all)
        return (_mk_cell([g[i] for i in idx]), _col(idx))[: max(nargout, 1)]
    a = _codes(v) if _is_char(v) else _arr(v, "sortrows")
    if a.ndim != 2:
        raise _err("sortrows: A must be a 2-D matrix.", "MATLAB:sortrows:inputDimensionMismatch")
    cols = spec or list(range(1, a.shape[1] + 1))
    if any(c == 0 or abs(c) > a.shape[1] for c in cols):
        raise _err("Column sorting vector must contain nonzero integers with absolute value no larger than the number of columns.", "MATLAB:sortrows:COLmismatchX")
    idx = np.arange(a.shape[0])
    for c in reversed(cols):  # stable passes from the last key to the first
        col = a[idx, abs(c) - 1]
        real = np.abs(col) if np.iscomplexobj(col) else col
        nan = np.isnan(real.astype(float)) if not np.issubdtype(real.dtype, np.integer) else np.zeros(real.shape, bool)
        desc = (c < 0) != desc_all
        key = np.where(nan, np.inf, real.astype(float))
        if desc:
            # descending: NaN first (MATLAB), stable among equals
            order = np.lexsort((np.arange(idx.size), -np.where(nan, -np.inf, real.astype(float))))
            order = np.lexsort((np.arange(idx.size), ~nan, -np.where(nan, 0, real.astype(float))))
            order = sorted(range(idx.size), key=lambda t: (not nan[t], -key[t] if not nan[t] else 0))
            order = np.array(order, dtype=int)
        else:
            order = np.argsort(key, kind="stable")
        idx = idx[order]
    out = a[idx]
    return (_from_codes(out) if _is_char(v) else NDArrayValue(out), _col(idx))[: max(nargout, 1)]


def register(builtins: Dict[str, Callable]) -> None:
    table = {
        "repmat": _repmat, "logspace": _logspace, "meshgrid": _grid("meshgrid", "xy"),
        "ndgrid": _grid("ndgrid", "ij"), "cell2mat": _cell2mat, "num2cell": _num2cell, "mat2cell": _mat2cell,
        "iscellstr": _iscellstr, "rot90": _rot90, "tril": _tri("tril", np.tril), "triu": _tri("triu", np.triu),
        "diag": _diag, "blkdiag": _blkdiag, "sub2ind": _sub2ind, "ind2sub": _ind2sub, "isequaln": _isequaln,
        "union": _setop("union"), "intersect": _setop("intersect"), "setdiff": _setop("setdiff"),
        "setxor": _setop("setxor"), "ismember": _ismember, "sortrows": _sortrows,
    }
    for k, v in table.items():
        builtins.setdefault(k, v)
    if "unique" in builtins:
        builtins["unique"] = _unique(builtins["unique"])
