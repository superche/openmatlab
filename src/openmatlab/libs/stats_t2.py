"""mean and median with the documented MATLAB option set (C-E5 #765 T2 burn-down).

mean(A), mean(A, 'all'), mean(A, dim), mean(A, vecdim), mean(..., outtype), mean(..., nanflag);
median takes the same options. outtype: 'default' | 'double' | 'native'; nanflag: 'includenan' |
'omitnan' | 'includemissing' | 'omitmissing'. Integer inputs are averaged exactly (no int64 overflow or
double rounding); 'native' rounds half away from zero and saturates. Non-array inputs (datetime,
duration, tables, sparse) keep their existing implementations.

Clean-room from the MATLAB documentation; no MATLAB or Octave source was consulted.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

from .burndown_builtins import _err, _is_text

OUTTYPES = ("default", "double", "native")
NANFLAGS = {"includenan": False, "omitnan": True, "includemissing": False, "omitmissing": True}



def _fsum(row: np.ndarray) -> float:
    """Correctly rounded sum; NumPy's sum where fsum cannot (non-finite input or intermediate overflow)."""
    if np.all(np.isfinite(row)):
        try:
            return math.fsum(row)
        except OverflowError:
            pass
    return row.sum()

def _parse(fn, args):
    a = args[0]
    from openmatlab.runtime.char_value import CharValue

    if isinstance(a, CharValue):
        x = np.array([[ord(c) for c in r] for r in a.rows], dtype=float).reshape(len(a.rows), -1) if a.rows else np.zeros((0, 0))
    else:
        x = np.asarray(a.backend_buffer())
    dims, outtype, omit, weights = None, "default", False, None
    rest = list(args[1:])
    for i in range(len(rest) - 1):
        if _is_text(rest[i]) and rest[i].text.lower() == "weights" and fn == "mean":
            weights = np.asarray(rest[i + 1].backend_buffer()).astype(float)
            rest = rest[:i] + rest[i + 2:]
            break
    for v in rest:
        if _is_text(v):
            t = v.text.lower()
            if t == "all":
                dims = "all"
            elif t in OUTTYPES:
                outtype = t
            elif t in NANFLAGS:
                omit = NANFLAGS[t]
            else:
                raise _err(f"{fn}: invalid option '{v.text}'.", f"MATLAB:{fn}:invalidFlag")
        else:
            if dims is not None:
                raise _err(f"{fn}: too many dimension arguments.", f"MATLAB:{fn}:invalidDim")
            d = np.asarray(v.backend_buffer()).reshape(-1)
            if d.size == 0 or np.any(d < 1) or np.any(d != np.round(d)):
                raise _err("Dimension argument must be a positive integer scalar or a vector of unique positive integers.",
                           f"MATLAB:{fn}:invalidDim")
            if np.unique(d).size != d.size:
                raise _err("Vector of dimensions must contain unique values.", f"MATLAB:{fn}:repeatedDims")
            dims = [int(k) - 1 for k in d]
    if fn == "mean":
        return x, dims, outtype, omit, weights
    return x, dims, outtype, omit


def _axes(x, dims):
    if dims == "all":
        return list(range(x.ndim)), True
    if dims is None:
        if x.ndim == 2 and x.shape == (0, 0):
            return [0], True  # mean([]) is NaN (1x1)
        nz = [i for i, k in enumerate(x.shape) if k != 1]
        return [nz[0] if nz else 0], False
    inside = [a for a in dims if a < x.ndim]  # dimensions beyond ndims are singletons
    return (inside or dims), False


def _frame(x, axes):
    """x reshaped to (n_out, k) with the reduced axes last; plus the output shape."""
    nd = max([x.ndim] + [a + 1 for a in axes])
    x = x.reshape(x.shape + (1,) * (nd - x.ndim))
    keep = [i for i in range(nd) if i not in axes]
    out_shape = [1 if i in axes else x.shape[i] for i in range(nd)]
    t = np.transpose(x, keep + list(axes))
    k = int(np.prod([x.shape[a] for a in axes])) if axes else 1
    flat = t.reshape(-1, k) if t.size else np.zeros((int(np.prod([x.shape[i] for i in keep])), k), dtype=x.dtype)
    return flat, keep, out_shape, x.shape


def _unframe(vals, keep, out_shape, full_shape):
    kshape = [full_shape[i] for i in keep]
    r = np.asarray(vals).reshape(kshape) if kshape else np.asarray(vals).reshape(())
    r = r.reshape([full_shape[i] if i in keep else 1 for i in range(len(full_shape))])
    while r.ndim > 2 and r.shape[-1] == 1:
        r = r.reshape(r.shape[:-1])
    if r.ndim < 2:
        r = r.reshape(r.shape + (1,) * (2 - r.ndim))
    return r


def _round_half_away(fr: Fraction) -> int:
    n = abs(fr)
    q = int(n)
    if n - q >= Fraction(1, 2):
        q += 1
    return q if fr >= 0 else -q


def _saturate(v, dtype):
    info = np.iinfo(dtype)
    return min(max(v, int(info.min)), int(info.max))


def _result_class(x, outtype, fn):
    k = x.dtype.kind
    if outtype == "double":
        return np.float64
    if outtype == "native" or (fn == "median" and outtype == "default" and k in "biu"):
        if k == "b":
            return np.float64 if fn == "mean" else np.bool_
        return x.dtype
    if x.dtype in (np.float32, np.complex64):
        return x.dtype
    return np.float64


def _mean(args, *, nargout=1):
    x, dims, outtype, omit, w = _parse("mean", args)
    axes, whole = _axes(x, dims)
    if w is not None:
        return (_weighted(x, w, axes, omit),)
    if x.ndim == 2 and x.shape == (0, 0) and dims is None:
        cls = _result_class(x, outtype, "mean")
        return (NDArrayValue(np.full((1, 1), np.nan, dtype=cls if np.dtype(cls).kind in "fc" else np.float64)),)
    if dims is not None and dims != "all" and all(a >= x.ndim for a in axes):
        cls = _result_class(x, outtype, "mean")
        return (NDArrayValue(x.astype(cls)),)
    flat, keep, out_shape, full = _frame(x, axes)
    cls = _result_class(x, outtype, "mean")
    if x.dtype.kind in "iu":
        res = []
        for row in flat:
            vals = [int(v) for v in row]
            if not vals:
                res.append(np.nan)
                continue
            fr = Fraction(sum(vals), len(vals))
            res.append(_saturate(_round_half_away(fr), x.dtype) if np.dtype(cls).kind in "iu" else float(fr))
        r = np.array(res, dtype=cls if not (np.dtype(cls).kind in "iu" and any(isinstance(v, float) for v in res)) else np.float64)
    else:
        f = flat.astype(np.complex128 if np.iscomplexobj(flat) else np.float64)
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            if omit:
                m = ~np.isnan(f)
                cnt = m.sum(axis=1)
                r = np.where(cnt > 0, np.where(m, f, 0).sum(axis=1) / np.maximum(cnt, 1), np.nan)
            elif not f.shape[1]:
                r = np.full(f.shape[0], np.nan)
            elif not np.iscomplexobj(f) and f.shape[0] <= 4096:  # correctly rounded sums (MATLAB-accurate)
                r = np.array([_fsum(row) for row in f]) / f.shape[1]
            else:
                r = f.sum(axis=1) / f.shape[1]
        if np.dtype(cls).kind in "fc":
            r = r.astype(np.complex64 if (cls == np.float32 or cls == np.complex64) and np.iscomplexobj(r) else
                         (np.float32 if cls in (np.float32, np.complex64) else r.dtype))
        elif np.dtype(cls).kind == "b":
            r = r.astype(np.float64)
    return (NDArrayValue(np.ascontiguousarray(_unframe(r, keep, out_shape, full))),)


def _weighted(x, w, axes, omit):
    if len(axes) != 1:
        raise _err("mean: 'Weights' requires a single operating dimension.", "MATLAB:mean:invalidWeights")
    ax = axes[0]
    x = x.astype(np.complex128 if np.iscomplexobj(x) else np.float64)
    if w.size == x.size and w.shape == x.shape:
        wb = w
    elif w.ndim <= 2 and min(w.shape) == 1 and w.size == (x.shape[ax] if ax < x.ndim else 1):
        shp = [1] * max(x.ndim, ax + 1)
        shp[ax] = w.size
        wb = w.reshape(shp)
    else:
        raise _err("mean: 'Weights' must be a vector matching the operating dimension or the same size as A.",
                   "MATLAB:mean:invalidWeights")
    if np.any(wb < 0):
        raise _err("mean: weights must be nonnegative.", "MATLAB:mean:invalidWeights")
    wb = np.broadcast_to(wb, x.shape)
    if omit:
        m = np.isnan(x)
        x, wb = np.where(m, 0, x), np.where(m, 0, wb)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (x * wb).sum(axis=ax, keepdims=True) / wb.sum(axis=ax, keepdims=True)
    return NDArrayValue(np.ascontiguousarray(r))


def _median(args, *, nargout=1):
    x, dims, outtype, omit = _parse("median", args)
    axes, whole = _axes(x, dims)
    cls = _result_class(x, outtype, "median")
    if x.ndim == 2 and x.shape == (0, 0) and dims is None:
        return (NDArrayValue(np.full((1, 1), np.nan, dtype=cls if np.dtype(cls).kind in "fc" else np.float64)),)
    if dims is not None and dims != "all" and all(a >= x.ndim for a in axes):
        return (NDArrayValue(x.astype(cls)),)
    flat, keep, out_shape, full = _frame(x, axes)
    res = []
    integer = x.dtype.kind in "iu"
    for row in flat:
        if integer:
            vals = sorted(int(v) for v in row)
            if not vals:
                res.append(np.nan)
                continue
            n = len(vals)
            fr = Fraction(vals[n // 2]) if n % 2 else Fraction(vals[n // 2 - 1] + vals[n // 2], 2)
            res.append(_saturate(_round_half_away(fr), x.dtype) if np.dtype(cls).kind in "iu" else float(fr))
            continue
        v = row.astype(np.complex128 if np.iscomplexobj(row) else np.float64)
        nanm = np.isnan(v)
        if nanm.any():
            if not omit:
                res.append(np.nan)
                continue
            v = v[~nanm]
        if v.size == 0:
            res.append(np.nan)
            continue
        if np.iscomplexobj(v):  # MATLAB sorts complex by abs, then angle
            v = v[np.lexsort((np.angle(v), np.abs(v)))]
        else:
            v = np.sort(v)
        n = v.size
        if n % 2:
            res.append(v[n // 2])
        else:
            a, b = v[n // 2 - 1], v[n // 2]
            res.append(a if a == b else (a + (b - a) / 2 if np.isfinite(a) and np.isfinite(b) and not np.iscomplexobj(v) else (a + b) / 2))
    if np.dtype(cls).kind in "iu" and not any(isinstance(r, float) for r in res):
        r = np.array(res, dtype=cls)
    elif np.dtype(cls).kind == "b":
        r = np.array(res, dtype=np.float64)
        r = r.astype(np.bool_) if not np.any(np.isnan(r)) else r
    else:
        cplx = any(isinstance(z, complex) or np.iscomplexobj(z) for z in res)
        r = np.array(res, dtype=np.complex128 if cplx else np.float64)
        if cls in (np.float32, np.complex64):
            r = r.astype(np.complex64 if cplx else np.float32)
    return (NDArrayValue(np.ascontiguousarray(_unframe(r, keep, out_shape, full))),)



def _mode_row(v):
    """(mode, frequency, all modes) of one slice; NaN values are ignored (documented)."""
    if v.dtype.kind in "fc":
        v = v[~np.isnan(v)]
    if v.size == 0:
        return None, 0, v
    vals, counts = np.unique(v, return_counts=True)
    f = counts.max()
    modes = vals[counts == f]
    return modes[0], int(f), modes


def _mode(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    x, dims, outtype, omit = _parse("mode", args)
    nanv = np.array(np.nan).astype(x.dtype) if x.dtype.kind in "fc" else np.zeros((), x.dtype)
    if x.ndim == 2 and x.shape == (0, 0) and dims is None:
        m = np.full((1, 1), np.nan) if x.dtype.kind not in "fc" else np.full((1, 1), np.nan, dtype=x.dtype)
        c = CellValue.from_obj(np.array([[NDArrayValue(np.zeros((0, 1), dtype=x.dtype if x.dtype.kind in "fc" else float))]], dtype=object))
        return (NDArrayValue(m), NDArrayValue(np.zeros((1, 1))), c)[:max(1, nargout)]
    axes, whole = _axes(x, dims)
    if dims is not None and dims != "all" and all(a >= x.ndim for a in axes):
        objs = np.empty(x.shape, dtype=object)
        for ix in np.ndindex(*x.shape):
            objs[ix] = NDArrayValue(x[ix].reshape(1, 1))
        f = np.where(np.isnan(x), 0.0, 1.0) if x.dtype.kind in "fc" else np.ones(x.shape)
        return (NDArrayValue(x.copy()), NDArrayValue(f), CellValue.from_obj(objs))[:max(1, nargout)]
    flat, keep, out_shape, full = _frame(x, axes)
    ms, fs, cs = [], [], []
    for row in flat:
        m, f, modes = _mode_row(row)
        if m is None:
            ms.append(np.nan)
            fs.append(0.0)
            cs.append(NDArrayValue(np.zeros((1, 0), dtype=x.dtype if x.dtype.kind in "fc" else float)))
        else:
            ms.append(m)
            fs.append(float(f))
            cs.append(NDArrayValue(np.asarray(modes, dtype=x.dtype).reshape(-1, 1)))
    if any(isinstance(m, float) and np.isnan(m) for m in ms) and x.dtype.kind not in "fc":
        mt = np.float64
    else:
        mt = x.dtype
    M = _unframe(np.array(ms, dtype=mt), keep, out_shape, full)
    F = _unframe(np.array(fs), keep, out_shape, full)
    objs = np.empty(len(cs), dtype=object)
    for i, c in enumerate(cs):
        objs[i] = c
    C = CellValue.from_obj(_unframe(objs, keep, out_shape, full)) if len(cs) else CellValue(rows=())
    return (NDArrayValue(np.ascontiguousarray(M)), NDArrayValue(np.ascontiguousarray(F)), C)[:max(1, nargout)]

def _is_plain(v):
    from openmatlab.runtime.char_value import CharValue

    return type(v) is NDArrayValue or isinstance(v, CharValue)


def _guard(new, old):
    def g(args, *, nargout=1):
        if not args:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        if not _is_plain(args[0]) or not all(_is_text(a) or type(a) is NDArrayValue for a in args[1:]):
            return old(args, nargout=nargout)
        return new(args, nargout=nargout)
    g.__wrapped__ = new
    return g


def register(builtins: Dict[str, Callable]) -> None:
    for name, fn in (("mean", _mean), ("median", _median), ("mode", _mode)):
        old = builtins.get(name)
        builtins[name] = _guard(fn, old) if old else fn
