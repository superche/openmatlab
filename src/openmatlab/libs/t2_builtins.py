"""Base-MATLAB functions surfaced by the T2 self-check tier (C-E5 #765 burn-down).

Matrix structure: issymmetric ishermitian isdiag istril istriu isbanded bandwidth.
Data: rescale rms rmse mape. Coordinates: cart2pol pol2cart cart2sph sph2cart.
Bits and dates: bitcmp bitset eomday. Paths and text: filesep pathsep erase.

Clean-room implementations from the documented behaviour and standard definitions (NumPy
only); no MATLAB or Octave source was consulted.
"""

from __future__ import annotations

import math
import os
import re
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

from .burndown_builtins import _cv, _err, _is_cell, _is_text, _need, _num, _out


def _bool(x):
    return (NDArrayValue(np.array([[bool(x)]])),)


def _mat(v, fn, allow_text=True):
    if _is_cell(v) or not hasattr(v, "backend_buffer") or (_is_text(v) and not allow_text):
        raise _err(f"{fn}: A must be a numeric, logical, or character matrix.", f"MATLAB:{fn}:invalidInput")
    a = _num(v, fn)
    if a.ndim > 2:
        raise _err(f"{fn}: A must be a 2-D matrix.", f"MATLAB:{fn}:invalidInput")
    return a


def _opt(v):
    return v.text.lower() if _is_text(v) else None


def _sym_common(args, fn, conj):
    _need(args, 1, fn)
    a = _mat(args[0], fn)
    skew, tol = False, 0.0
    for v in args[1:]:
        o = _opt(v)
        if o is not None:
            if o not in ("skew", "nonskew"):
                raise _err(f"{fn}: SKEWOPT must be 'skew' or 'nonskew'.", f"MATLAB:{fn}:invalidOption")
            skew = o == "skew"
        else:
            t = _num(v, fn).reshape(-1) if hasattr(v, "backend_buffer") and not _is_cell(v) else None
            if t is None or t.size != 1 or not (t[0] >= 0):
                raise _err(f"{fn}: TOL must be a scalar >= 0.", f"MATLAB:{fn}:invalidTol")
            tol = float(t[0])
    if a.shape[0] != a.shape[1]:
        return _bool(False)
    if a.size == 0:
        return _bool(True)
    t = a.conj().T if conj else a.T
    b = -t if skew else t
    if tol == 0:
        return _bool(np.array_equal(a, b))
    n = np.linalg.norm(a, np.inf)
    return _bool(np.linalg.norm(a - b, np.inf) <= tol * n)


def _issymmetric(args, *, nargout=1):
    return _sym_common(args, "issymmetric", False)


def _ishermitian(args, *, nargout=1):
    return _sym_common(args, "ishermitian", True)


def _band(a):
    if a.size == 0:
        return 0, 0
    r, c = np.nonzero(a)
    if r.size == 0:
        return 0, 0
    d = c - r
    return int(max(0, -d.min())), int(max(0, d.max()))


def _bandwidth(args, *, nargout=1):
    _need(args, 1, "bandwidth")
    a = _mat(args[0], "bandwidth", allow_text=False)
    lo, up = _band(a)
    if len(args) > 1:
        o = _opt(args[1])
        if o not in ("lower", "upper"):
            raise _err("bandwidth: TYPE must be 'lower' or 'upper'.", "MATLAB:bandwidth:invalidType")
        return (_out(float(lo if o == "lower" else up)),)
    return (_out(float(lo)), _out(float(up)))[:max(1, nargout)]


def _isbanded(args, *, nargout=1):
    _need(args, 3, "isbanded")
    a = _mat(args[0], "isbanded")
    lo, up = (_num(v, "isbanded").reshape(-1) for v in args[1:3])
    if lo.size != 1 or up.size != 1 or lo[0] < 0 or up[0] < 0 or lo[0] != np.floor(lo[0]) or up[0] != np.floor(up[0]):
        raise _err("isbanded: LOWER and UPPER must be non-negative integers.", "MATLAB:isbanded:invalidBand")
    l2, u2 = _band(a)
    return _bool(l2 <= lo[0] and u2 <= up[0])


def _tri_pred(fn, test):
    def f(args, *, nargout=1):
        _need(args, 1, fn)
        a = _mat(args[0], fn)
        if a.size == 0:
            return _bool(True)
        lo, up = _band(a)
        return _bool(test(lo, up))
    return f


def _rescale(args, *, nargout=1):
    _need(args, 1, "rescale")
    single = args[0].matlab_class() == "single"
    a = _num(args[0], "rescale").astype(float)
    pos = [v for v in args[1:] if not _is_text(v)]
    l, u = (float(_num(pos[0], "rescale").reshape(-1)[0]), float(_num(pos[1], "rescale").reshape(-1)[0])) if len(pos) >= 2 else (0.0, 1.0)
    opts = {}
    named = [v for v in args[1:]]
    i = 0
    while i < len(named):
        if _is_text(named[i]) and i + 1 < len(named):
            opts[named[i].text.lower()] = _num(named[i + 1], "rescale")
            i += 2
        else:
            i += 1
    if a.size == 0:
        return (_out(a.astype(np.float32) if single else a),)
    lo = float(opts["inputmin"].reshape(-1)[0]) if "inputmin" in opts else np.min(a)
    hi = float(opts["inputmax"].reshape(-1)[0]) if "inputmax" in opts else np.max(a)
    x = np.clip(a, lo, hi)
    with np.errstate(invalid="ignore", divide="ignore"):
        if hi == lo:
            r = np.full(a.shape, l)
        else:
            r = l + (x - lo) / (hi - lo) * (u - l)
    return (_out(r.astype(np.float32) if single else r),)


def _dims(a, args, k):
    """Reduction dims (0-based tuple) from DIM / VECDIM / 'all' at args[k], default first non-singleton."""
    if len(args) > k and _is_text(args[k]) and args[k].text.lower() == "all":
        return tuple(range(max(a.ndim, 2)))
    if len(args) > k and not _is_text(args[k]):
        d = _num(args[k], "dim").reshape(-1)
        if d.size and np.all(d >= 1) and np.all(d == np.floor(d)):
            return tuple(sorted(set(int(x) - 1 for x in d)))
        raise _err("Dimension argument must be a positive integer scalar or a vector of unique positive integers.",
                   "MATLAB:getdimarg:invalidDim")
    nz = [i for i, s in enumerate(a.shape) if s != 1]
    return (nz[0] if nz else 0,)


def _masked_mean(d, excl, dims):
    nd = max(d.ndim, max(dims) + 1, 2)
    d = d.reshape(d.shape + (1,) * (nd - d.ndim))
    excl = excl.reshape(d.shape)
    keep = np.where(excl, 0.0, 1.0)
    vals = np.where(excl, 0.0, d)
    n = keep.sum(axis=dims, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return vals.sum(axis=dims, keepdims=True) / n


def _flags(args):
    fl, rest = set(), []
    for v in args:
        t = v.text.lower() if _is_text(v) else ""
        if t in ("omitnan", "omitmissing", "includenan", "includemissing", "omitzero", "includezero"):
            fl.add(t.replace("missing", "nan"))
        else:
            rest.append(v)
    return rest, fl


def _rms(args, *, nargout=1):
    args, fl = _flags(args)
    _need(args, 1, "rms")
    a = _num(args[0], "rms")
    if a.shape == (0, 0) and len(args) == 1:
        return (_out(np.array([[np.nan]])),)
    sq = np.abs(a) ** 2
    excl = np.isnan(sq) if "omitnan" in fl else np.zeros(sq.shape, bool)
    return (_out(np.sqrt(_masked_mean(sq, excl, _dims(a, args, 1)))),)


def _pair_metric(fn, f, post=lambda r: r):
    def g(args, *, nargout=1):
        args, fl = _flags(args)
        _need(args, 2, fn)
        a, b = _num(args[0], fn), _num(args[1], fn)
        try:
            a, b = np.broadcast_arrays(a, b)
        except ValueError:
            raise _err("Arrays have incompatible sizes for this operation.", "MATLAB:sizeDimensionsMustMatch")
        with np.errstate(divide="ignore", invalid="ignore"):
            d = f(a, b)
        excl = np.zeros(d.shape, bool)
        if "omitnan" in fl:
            excl |= np.isnan(a) | np.isnan(b)
        if "omitzero" in fl:
            excl |= b == 0
        return (_out(post(_masked_mean(d, excl, _dims(d, args, 2)))),)
    return g


def _cart2pol(args, *, nargout=1):
    if len(args) == 1:
        m = _num(args[0], "cart2pol")
        x, y = m[:, 0], m[:, 1]
        z = m[:, 2] if m.shape[1] > 2 else None
        th, r = np.arctan2(y, x), np.hypot(x, y)
        if nargout <= 1:
            cols = [th, r] + ([z] if z is not None else [])
            return (_out(np.column_stack(cols)),)
        outs = [th[:, None], r[:, None]] + ([z[:, None]] if z is not None else [])
        return tuple(_out(o) for o in outs)[:nargout]
    x, y = np.broadcast_arrays(_num(args[0], "cart2pol"), _num(args[1], "cart2pol"))
    outs = [np.arctan2(y, x), np.hypot(x, y)]
    if len(args) > 2:
        outs.append(np.broadcast_to(_num(args[2], "cart2pol"), x.shape))
    return tuple(_out(o) for o in outs)[:max(1, nargout)]


def _pol2cart(args, *, nargout=1):
    if len(args) == 1:
        m = _num(args[0], "pol2cart")
        th, r = m[:, 0], m[:, 1]
        z = m[:, 2] if m.shape[1] > 2 else None
        x, y = r * np.cos(th), r * np.sin(th)
        if nargout <= 1:
            return (_out(np.column_stack([x, y] + ([z] if z is not None else []))),)
        return tuple(_out(o[:, None]) for o in [x, y] + ([z] if z is not None else []))[:nargout]
    th, r = np.broadcast_arrays(_num(args[0], "pol2cart"), _num(args[1], "pol2cart"))
    outs = [r * np.cos(th), r * np.sin(th)]
    if len(args) > 2:
        outs.append(np.broadcast_to(_num(args[2], "pol2cart"), th.shape))
    return tuple(_out(o) for o in outs)[:max(1, nargout)]


def _cart2sph(args, *, nargout=1):
    if len(args) == 1:
        m = _num(args[0], "cart2sph")
        x, y, z = m[:, 0], m[:, 1], m[:, 2]
    else:
        _need(args, 3, "cart2sph")
        x, y, z = np.broadcast_arrays(*(_num(v, "cart2sph") for v in args[:3]))
    az, el, r = np.arctan2(y, x), np.arctan2(z, np.hypot(x, y)), np.sqrt(x * x + y * y + z * z)
    if len(args) == 1 and nargout <= 1:
        return (_out(np.column_stack([az, el, r])),)
    if len(args) == 1:
        az, el, r = az[:, None], el[:, None], r[:, None]
    return tuple(_out(o) for o in (az, el, r))[:max(1, nargout)]


def _sph2cart(args, *, nargout=1):
    if len(args) == 1:
        m = _num(args[0], "sph2cart")
        az, el, r = m[:, 0], m[:, 1], m[:, 2]
    else:
        _need(args, 3, "sph2cart")
        az, el, r = np.broadcast_arrays(*(_num(v, "sph2cart") for v in args[:3]))
    x, y, z = r * np.cos(el) * np.cos(az), r * np.cos(el) * np.sin(az), r * np.sin(el)
    if len(args) == 1 and nargout <= 1:
        return (_out(np.column_stack([x, y, z])),)
    if len(args) == 1:
        x, y, z = x[:, None], y[:, None], z[:, None]
    return tuple(_out(o) for o in (x, y, z))[:max(1, nargout)]


_INT_BITS = {"uint8": 8, "uint16": 16, "uint32": 32, "uint64": 64, "int8": 8, "int16": 16, "int32": 32, "int64": 64}


def _bitcmp(args, *, nargout=1):
    _need(args, 1, "bitcmp")
    v = args[0]
    raw = np.asarray(v.backend_buffer())
    cls = v.matlab_class()
    if cls in _INT_BITS:
        return (NDArrayValue((~raw.astype(raw.dtype)).reshape(raw.shape if raw.ndim else (1, 1))),)
    a = _num(v, "bitcmp")
    if len(args) > 1:
        name = args[1].text if _is_text(args[1]) else None
        bits = _INT_BITS.get(name, None) if name else int(_num(args[1], "bitcmp").reshape(-1)[0])
        if name and name.startswith("int"):
            return (_out(-a - 1),)
    else:
        bits = 32 if cls == "single" else 53
    if np.any(a < 0) or np.any(a != np.floor(a)) or np.any(a >= 2.0 ** bits):
        raise _err("Double inputs must have integer values in the range of ASSUMEDTYPE.", "MATLAB:bitcmp:outOfRange")
    return (_out((2.0 ** bits - 1) - a),)


def _bitset(args, *, nargout=1):
    _need(args, 2, "bitset")
    v = args[0]
    cls = v.matlab_class()
    a = np.asarray(v.backend_buffer())
    if a.ndim == 0:
        a = a.reshape(1, 1)
    bit = _num(args[1], "bitset").astype(np.int64)
    val = _num(args[2], "bitset") != 0 if len(args) > 2 else np.array(True)
    maxbits = _INT_BITS.get(cls, 53 if cls == "double" else 24)
    if np.any(bit < 1) or np.any(bit > maxbits):
        raise _err("Bit position must be between 1 and the number of bits in ASSUMEDTYPE.", "MATLAB:bitset:outOfRange")
    if cls in _INT_BITS:
        a2, b2, v2 = np.broadcast_arrays(a, bit, val)
        out = a2.astype(np.int64 if cls.startswith("int") else np.uint64).copy()
        mask = (np.ones_like(out) << (b2.astype(out.dtype) - 1))
        out = np.where(v2, out | mask, out & ~mask)
        return (NDArrayValue(out.astype(a.dtype)),)
    af = a.astype(np.float64)
    a2, b2, v2 = np.broadcast_arrays(af, bit, val)
    ai = a2.astype(np.uint64)
    mask = np.left_shift(np.uint64(1), (b2 - 1).astype(np.uint64))
    out = np.where(v2, ai | mask, ai & ~mask).astype(np.float64)
    return (NDArrayValue(out.astype(np.float32) if cls == "single" else out),)


def _eomday(args, *, nargout=1):
    _need(args, 2, "eomday")
    y, m = np.broadcast_arrays(_num(args[0], "eomday"), _num(args[1], "eomday"))
    days = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=float)
    mi = m.astype(int)
    if np.any(mi < 1) or np.any(mi > 12):
        raise _err("Index exceeds the number of array elements.", "MATLAB:badsubscript")
    leap = ((y % 4 == 0) & (y % 100 != 0)) | (y % 400 == 0)
    return (_out(days[mi - 1] + ((mi == 2) & leap)),)


def _filesep(args, *, nargout=1):
    return (_cv(os.sep),)


def _pathsep(args, *, nargout=1):
    return (_cv(os.pathsep),)


def _erase(args, *, nargout=1):
    _need(args, 2, "erase")
    s, p = args[0], args[1]
    pats = [x.text for x in (p.cells_flat() if hasattr(p, "cells_flat") else _flat_cell(p))] if _is_cell(p) else _texts(p)
    pats = sorted(pats, key=len, reverse=True)

    def er(t):
        if not pats:
            return t
        out, i = [], 0
        while i < len(t):
            for q in pats:
                if q and t.startswith(q, i):
                    i += len(q)
                    break
            else:
                out.append(t[i])
                i += 1
        return "".join(out)

    if _is_cell(s):
        from .burndown_builtins import _cell

        items = _flat_cell(s)
        return (_cell([_cv(er(x.text)) for x in items], s.shape),)
    if not _is_text(s):
        raise _err("First argument must be text.", "MATLAB:erase:InvalidInput")
    if getattr(s, "is_string", False) or type(s).__name__ == "StringValue":
        return _string_map(s, er)
    return (type(s)(er(s.text)),)


def _texts(p):
    if not _is_text(p):
        raise _err("Second argument must be text.", "MATLAB:erase:InvalidInput")
    if type(p).__name__ == "StringValue" and hasattr(p, "items"):
        return [str(x) for x in p.items()]
    return [p.text]


def _flat_cell(c):
    r, k = c.shape
    return [c.get(i, j) for j in range(k) for i in range(r)]


def _string_map(s, f):
    if hasattr(s, "map_text"):
        return (s.map_text(f),)
    return (type(s)(f(s.text)),)


def _tensorprod(args, *, nargout=1):
    _need(args, 2, "tensorprod")
    a, b = _num(args[0], "tensorprod"), _num(args[1], "tensorprod")
    rest, nda = list(args[2:]), None
    for i in range(len(rest) - 1):
        if _is_text(rest[i]) and rest[i].text.lower() == "numdimensionsa":
            nda = int(_num(rest[i + 1], "tensorprod").reshape(-1)[0])
            rest = rest[:i] + rest[i + 2:]
            break
    na = max(a.ndim, 2, nda or 0)
    if rest and _is_text(rest[0]) and rest[0].text.lower() == "all":
        if a.size != b.size or a.reshape(-1).shape != b.reshape(-1).shape:
            raise _err("tensorprod: the sizes of A and B must match for 'all'.", "MATLAB:tensorprod:SizeMismatch")
        return (_out(np.sum(a.reshape(-1, order="F") * b.reshape(-1, order="F"))),)
    da = [int(x) - 1 for x in _num(rest[0], "tensorprod").reshape(-1)] if rest else []
    db = [int(x) - 1 for x in _num(rest[1], "tensorprod").reshape(-1)] if len(rest) > 1 else list(da)
    if len(da) != len(db) or any(x < 0 for x in da + db):
        raise _err("tensorprod: dimA and dimB must have the same number of positive dimensions.",
                   "MATLAB:tensorprod:DimMismatch")
    na = max([na] + [x + 1 for x in da])
    nb = max([b.ndim, 2] + [x + 1 for x in db])
    a = a.reshape(a.shape + (1,) * (na - a.ndim))
    b = b.reshape(b.shape + (1,) * (nb - b.ndim))
    if any(a.shape[i] != b.shape[j] for i, j in zip(da, db)):
        raise _err("tensorprod: contracted dimensions of A and B must have the same size.",
                   "MATLAB:tensorprod:SizeMismatch")
    r = np.tensordot(a, b, axes=(da, db)) if da else np.multiply.outer(a, b)
    shape = list(r.shape)
    while len(shape) > 2 and shape[-1] == 1:
        shape.pop()
    while len(shape) < 2:
        shape.append(1)
    return (_out(r.reshape(shape)),)


def _prctile_along(x, p, ax):
    """MATLAB-style percentile (midpoint positions, linear interpolation, clamped) along axis ``ax``."""
    xs = np.sort(x, axis=ax)
    n = xs.shape[ax]
    pos = np.clip(n * p / 100.0 - 0.5, 0, n - 1)
    lo = int(np.floor(pos))
    hi = min(lo + 1, n - 1)
    f = pos - lo
    a, b = np.take(xs, [lo], axis=ax), np.take(xs, [hi], axis=ax)
    return a + f * (b - a)


def _normalize(args, *, nargout=1):
    _need(args, 1, "normalize")
    single = args[0].matlab_class() == "single"
    a = _num(args[0], "normalize").astype(float)
    rest = list(args[1:])
    if rest and not _is_text(rest[0]):
        dim = int(_num(rest.pop(0), "normalize").reshape(-1)[0]) - 1
    else:
        nz = [i for i, k in enumerate(a.shape) if k != 1]
        dim = nz[0] if nz else 0
    if dim >= a.ndim:
        a = a.reshape(a.shape + (1,) * (dim + 1 - a.ndim))
    method, center, scale = None, None, None
    i = 0
    while i < len(rest):
        m = rest[i].text.lower() if _is_text(rest[i]) else ""
        nxt = rest[i + 1] if i + 1 < len(rest) else None
        opt = None
        if nxt is not None and not (_is_text(nxt) and nxt.text.lower() in ("zscore", "norm", "scale", "range", "center", "medianiqr")):
            opt = nxt.text.lower() if _is_text(nxt) else _num(nxt, "normalize")
        if m in ("zscore", "norm", "range", "medianiqr"):
            method = (m, opt)
        elif m == "center":
            center = opt if opt is not None else "mean"
        elif m == "scale":
            scale = opt if opt is not None else "std"
        else:
            raise _err(f"normalize: unknown method '{m}'.", "MATLAB:normalize:InvalidMethod")
        i += 2 if opt is not None else 1
    ax = dim
    mean = lambda x: np.mean(x, axis=ax, keepdims=True)
    med = lambda x: np.median(x, axis=ax, keepdims=True)
    n = a.shape[ax]
    std = lambda x: np.std(x, axis=ax, ddof=1 if n > 1 else 0, keepdims=True)
    iqr = lambda x: _prctile_along(x, 75, ax) - _prctile_along(x, 25, ax)
    mad = lambda x: med(np.abs(x - med(x)))

    def stat(spec, kind):
        if isinstance(spec, np.ndarray):
            return spec
        table = {"mean": mean, "median": med, "std": std, "mad": mad, "iqr": iqr,
                 "first": lambda x: np.take(x, [0], axis=ax)}
        if spec not in table:
            raise _err(f"normalize: unknown {kind} option '{spec}'.", "MATLAB:normalize:InvalidOption")
        return table[spec](a)

    with np.errstate(divide="ignore", invalid="ignore"):
        if center is not None or scale is not None:
            c = stat(center, "center") if center is not None else np.zeros((1,) * a.ndim)
            sc = stat(scale, "scale") if scale is not None else np.ones((1,) * a.ndim)
        elif method is None or method[0] == "zscore":
            kind = method[1] if method and method[1] is not None else "std"
            if kind == "robust":
                c, sc = med(a), mad(a)
            else:
                c, sc = mean(a), std(a)
        elif method[0] == "norm":
            pv = float(np.asarray(method[1]).reshape(-1)[0]) if method[1] is not None else 2.0
            c = np.zeros((1,) * a.ndim)
            sc = np.max(np.abs(a), axis=ax, keepdims=True) if np.isinf(pv) else np.sum(np.abs(a) ** pv, axis=ax, keepdims=True) ** (1 / pv)
        elif method[0] == "range":
            lo_hi = np.asarray(method[1], dtype=float).reshape(-1) if method[1] is not None else np.array([0.0, 1.0])
            mn, mx = np.min(a, axis=ax, keepdims=True), np.max(a, axis=ax, keepdims=True)
            sc = (mx - mn) / (lo_hi[1] - lo_hi[0])
            c = mn - lo_hi[0] * sc
        else:  # medianiqr
            c, sc = med(a), iqr(a)
        z = (a - c) / sc
    cast = (lambda x: _out(x.astype(np.float32))) if single else _out
    outs = (cast(z), cast(np.broadcast_to(c, c.shape)), cast(np.broadcast_to(sc, sc.shape)))
    return outs[:max(1, nargout)]


def _civil(z):
    """(y, m, d) from days since 1970-01-01, proleptic Gregorian (any integer)."""
    z = z + 719468
    era = z // 146097  # Python floors already
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    return y + (m <= 2), m, d


def _vec_of(dn):
    if not np.isfinite(dn):
        return [np.nan] * 6
    day = math.floor(dn)
    secs = round((dn - day) * 86400.0, 6)
    if secs >= 86400:
        day, secs = day + 1, secs - 86400
    y, m, d = _civil(int(day) - 719529)
    h = int(secs // 3600)
    mi = int((secs - 3600 * h) // 60)
    sec = round(secs - 3600 * h - 60 * mi, 6)
    return [float(y), float(m), float(d), float(h), float(mi), sec]


_MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
_FMT_TOKENS = [("yyyy", r"(?P<y>[-+]?\d{1,4})"), ("yy", r"(?P<yy>\d{2})"), ("mmmm", r"(?P<mon>[A-Za-z]+)"),
               ("mmm", r"(?P<mon>[A-Za-z]{3})"), ("mm", r"(?P<m>\d{1,2})"), ("dddd", r"[A-Za-z]+"),
               ("ddd", r"[A-Za-z]{3}"), ("dd", r"(?P<d>\d{1,2})"), ("HH", r"(?P<H>\d{1,2})"),
               ("MM", r"(?P<M>\d{1,2})"), ("SS", r"(?P<S>\d{1,2})"), ("FFF", r"(?P<F>\d{1,3})"),
               ("AM", r"(?P<P>[AaPp][Mm])"), ("PM", r"(?P<P>[AaPp][Mm])")]
_STD_FORMATS = ["dd-mmm-yyyy HH:MM:SS", "dd-mmm-yyyy", "mm/dd/yy", "mm/dd", "HH:MM:SS", "HH:MM:SS PM", "HH:MM",
                "HH:MM PM", "mm/dd/yyyy", "mmm.dd,yyyy HH:MM:SS", "mmm.dd,yyyy", "yyyy/mm/dd", "yyyy-mm-dd",
                "yyyy-mm-dd HH:MM:SS", "yyyy-mm-ddTHH:MM:SS", "yyyy-mm-ddTHH:MM:SS.FFF", "yyyy-mm", "yyyy",
                "yyyymmddTHHMMSS", "dd-mmm-yyyy HH:MM", "mmmyy", "dd mmm yyyy", "dd mmm yyyy HH:MM:SS",
                "mmm dd yyyy HH:MM:SS", "mmm dd yyyy", "dd.mmm.yyyy HH:MM:SS", "dd.mmm.yyyy", "mmm.dd.yyyy HH:MM:SS",
                "mmm.dd.yyyy", "mm/dd/yyyy HH:MM", "mm/dd/yyyy HH:MM:SS", "yyyy/mm/dd HH:MM:SS", "yyyy/mm/dd HH:MM",
                "yyyy-mm-dd HH:MM", "mmm-dd-yyyy HH:MM:SS", "mmm-dd-yyyy"]


def _fmt_regex(fmt):
    out, i = [], 0
    while i < len(fmt):
        for tok, rx in _FMT_TOKENS:
            if fmt.startswith(tok, i):
                out.append(rx)
                i += len(tok)
                break
        else:
            out.append(re.escape(fmt[i]))
            i += 1
    rx = "".join(out)
    seen = set()  # a group name may only appear once
    def dedupe(m):
        n = m.group(1)
        if n in seen:
            return "(?:"
        seen.add(n)
        return m.group(0)
    return re.compile(r"^\s*" + re.sub(r"\(\?P<(\w+)>", dedupe, rx) + r"\s*$")


def _parse_with(text, fmt, prefix=False):
    rx = _fmt_regex(fmt)
    m = re.compile(rx.pattern[:-len(r"\s*$")]).match(text) if prefix else rx.match(text)
    if not m:
        return None
    g = {k: v for k, v in m.groupdict().items() if v is not None}
    now_y = float(_dt_now().year)
    has_date = any(k in g for k in ("y", "yy", "mon", "m", "d"))
    y = float(g["y"]) if "y" in g else (2000.0 + float(g["yy"]) if "yy" in g and float(g["yy"]) < 50 else
                                        1900.0 + float(g["yy"]) if "yy" in g else now_y)
    if "mon" in g:
        k = g["mon"][:3].lower()
        if k not in _MON:
            return None
        mo = float(_MON.index(k) + 1)
    else:
        mo = float(g["m"]) if "m" in g else 1.0
    if "d" in g:
        d = float(g["d"])
    elif "y" in g and "m" not in g and "mon" not in g:
        d = 0.0 if fmt == "yyyy" else 1.0
    else:
        d = 1.0
    if not has_date:
        y, mo, d = now_y, 1.0, 1.0
    h = float(g.get("H", 0))
    if "P" in g:
        if h > 12:
            return None
        h = h % 12 + (12 if g["P"].lower() == "pm" else 0)
    sec = float(g.get("S", 0)) + (float("0." + g["F"]) if "F" in g else 0.0)
    if mo < 1 or mo > 12 or d > 31 or h > 24 or float(g.get("M", 0)) > 59 or sec >= 61:
        return None
    return [y, mo, d, h, float(g.get("M", 0)), round(sec, 6)]


def _dt_now():
    import datetime as _dt

    return _dt.datetime.now()


def _parse_date(text, fmt=None):
    t = text.strip()
    if t.endswith("Z"):
        t = t[:-1]
    for f in ([fmt] if fmt else _STD_FORMATS):
        v = _parse_with(t, f, prefix=bool(fmt))
        if v is not None:
            return v
    raise _err(f"datevec: none of the standard formats match the DATE string.", "MATLAB:datevec:Inputs")


def _datevec(args, *, nargout=1):
    _need(args, 1, "datevec")
    v = args[0]
    fmt = args[1].text if len(args) > 1 and _is_text(args[1]) else None
    if _is_text(v) or _is_cell(v):
        texts = [x.text for x in _flat_cell(v)] if _is_cell(v) else ([r for r in v.rows] if v.rows else [""])
        rows = [_parse_date(t, fmt) for t in texts]
        shape = (len(rows), 1)
    else:
        if type(v).__name__ == "DatetimeValue":
            a = np.asarray(v.v, dtype=float)
        else:
            a = np.asarray(v.backend_buffer(), dtype=float)
        a = a.reshape(1, 1) if a.ndim == 0 else a
        shape = a.shape
        rows = [_vec_of(float(x)) for x in a.reshape(-1, order="F")]
    m = np.array(rows, dtype=float).reshape(-1, 6) if rows else np.zeros((0, 6))
    if nargout <= 1:
        return (_out(m),)
    return tuple(_out(m[:, k].reshape(shape, order="F")) for k in range(6))[:nargout]


def _isuniform(args, *, nargout=1):
    _need(args, 1, "isuniform")
    v = args[0]
    a = _num(v, "isuniform").reshape(-1)
    if a.size < 2 or (a.ndim and min(np.shape(np.asarray(v.backend_buffer() if not _is_text(v) else a))) > 1
                      and np.asarray(v.backend_buffer()).ndim > 1 and sum(k > 1 for k in np.shape(v.backend_buffer())) > 1):
        return (NDArrayValue(np.array([[False]])), _out(np.nan))[:max(1, nargout)]
    d = np.diff(a)
    if not np.all(np.isfinite(a)):
        return (NDArrayValue(np.array([[False]])), _out(np.nan))[:max(1, nargout)]
    is_int = v.matlab_class() in _INT_BITS or v.matlab_class() in ("logical", "char")
    if is_int:
        ok = bool(np.all(d == d[0]))
    else:
        tol = 4 * np.spacing(np.max(np.abs(a)).astype(np.float32 if v.matlab_class() == "single" else float))
        ok = bool(np.all(np.abs(d - d[0]) <= tol)) if d[0] != 0 or np.all(d == 0) else False
    step = float(d[0]) if ok else np.nan
    return (NDArrayValue(np.array([[ok]])), _out(step))[:max(1, nargout)]


def _vecnorm(args, *, nargout=1):
    _need(args, 1, "vecnorm")
    a = _num(args[0], "vecnorm")
    p = float(_num(args[1], "vecnorm").reshape(-1)[0]) if len(args) > 1 else 2.0
    if len(args) > 2:
        ax = int(_num(args[2], "vecnorm").reshape(-1)[0]) - 1
    else:
        nz = [i for i, k in enumerate(a.shape) if k != 1]
        ax = nz[0] if nz else 0
    if ax >= a.ndim:
        a = a.reshape(a.shape + (1,) * (ax + 1 - a.ndim))
    if not p > 0:
        raise _err("vecnorm: P must be positive.", "MATLAB:vecnorm:invalidP")
    m = np.abs(a)
    r = np.max(m, axis=ax, keepdims=True) if np.isinf(p) else np.sum(m ** p, axis=ax, keepdims=True) ** (1 / p)
    return (_out(r),)


def _pi_trig(fn, f):
    def g(args, *, nargout=1):
        _need(args, 1, fn)
        a = _num(args[0], fn)
        r = f(a)
        return (_out(r.astype(np.float32) if args[0].matlab_class() == "single" else r),)
    return g


def _sinpi(a):
    r = np.mod(a, 2.0)
    out = np.sin(np.pi * r)
    out = np.where(r == np.floor(r), 0.0, out)
    out = np.where(r == 0.5, 1.0, np.where(r == 1.5, -1.0, out))
    return np.where(np.isfinite(a), out, np.nan)


def _cospi(a):
    r = np.mod(a, 2.0)
    out = np.cos(np.pi * r)
    out = np.where((r == 0.5) | (r == 1.5), 0.0, out)
    out = np.where(r == 0, 1.0, np.where(r == 1, -1.0, out))
    return np.where(np.isfinite(a), out, np.nan)


def _polyarea(args, *, nargout=1):
    _need(args, 2, "polyarea")
    x, y = _num(args[0], "polyarea"), _num(args[1], "polyarea")
    if x.shape != y.shape:
        raise _err("polyarea: X and Y must have the same shape.", "MATLAB:polyarea:XYSizeMismatch")
    if len(args) > 2:
        ax = int(_num(args[2], "polyarea").reshape(-1)[0]) - 1
    else:
        nz = [i for i, k in enumerate(x.shape) if k != 1]
        ax = nz[0] if nz else 0
    xr, yr = np.roll(x, -1, axis=ax), np.roll(y, -1, axis=ax)
    return (_out(np.abs(np.sum(x * yr - xr * y, axis=ax, keepdims=True)) / 2),)


def _pagetrans(conj):
    def g(args, *, nargout=1):
        _need(args, 1, "pagetranspose")
        a = np.asarray(args[0].backend_buffer())
        a = a.reshape(1, 1) if a.ndim == 0 else a
        r = np.swapaxes(a, 0, 1)
        return (NDArrayValue(np.conj(r) if conj else r),)
    return g


def _swapbytes(args, *, nargout=1):
    _need(args, 1, "swapbytes")
    a = np.asarray(args[0].backend_buffer())
    if a.dtype == np.bool_ or a.dtype.kind not in "iuf":
        raise _err("swapbytes: input must be a numeric array.", "MATLAB:swapbytes:invalidInput")
    return (NDArrayValue(a.byteswap()),)


def _computer(args, *, nargout=1):
    import platform
    import sys

    mach = platform.machine().lower()
    if sys.platform.startswith("linux"):
        arch = "GLNXA64" if "64" in mach else "GLNX86"
    elif sys.platform == "darwin":
        arch = "MACA64" if mach in ("arm64", "aarch64") else "MACI64"
    else:
        arch = "PCWIN64"
    if args and _is_text(args[0]) and args[0].text.lower() == "arch":
        return (_cv(arch.lower().replace("glnxa64", "glnxa64")),)
    outs = (_cv(arch), _out(float(2 ** 48 - 1)), _cv("L"))
    return outs[:max(1, nargout)]


def _rectint(args, *, nargout=1):
    _need(args, 2, "rectint")
    a, b = _num(args[0], "rectint"), _num(args[1], "rectint")
    if a.shape[-1] != 4 or b.shape[-1] != 4:
        raise _err("rectint: A and B must have 4 columns.", "MATLAB:rectint:invalidInput")
    a, b = a.reshape(-1, 4), b.reshape(-1, 4)
    ax0, ay0, ax1, ay1 = a[:, 0:1], a[:, 1:2], a[:, 0:1] + a[:, 2:3], a[:, 1:2] + a[:, 3:4]
    bx0, by0, bx1, by1 = b[:, 0], b[:, 1], b[:, 0] + b[:, 2], b[:, 1] + b[:, 3]
    w = np.clip(np.minimum(ax1, bx1) - np.maximum(ax0, bx0), 0, None)
    h = np.clip(np.minimum(ay1, by1) - np.maximum(ay0, by0), 0, None)
    return (_out(w * h),)


def _subspace(args, *, nargout=1):
    _need(args, 2, "subspace")
    a, b = _num(args[0], "subspace"), _num(args[1], "subspace")
    qa, _ = np.linalg.qr(a)
    qb, _ = np.linalg.qr(b)
    if qa.shape[1] < qb.shape[1]:
        qa, qb = qb, qa
    c = qb - qa @ (qa.conj().T @ qb)
    sv = np.linalg.svd(c, compute_uv=False)
    return (_out(float(np.arcsin(min(1.0, sv.max() if sv.size else 0.0)))),)


def _tol_default(a):
    return 1e-6 if a.dtype == np.float64 else 1e-4


def _uniquetol(args, *, nargout=1):
    _need(args, 1, "uniquetol")
    single = args[0].matlab_class() == "single"
    a = _num(args[0], "uniquetol")
    rest = list(args[1:])
    tol = 1e-4 if single else 1e-12
    if rest and not _is_text(rest[0]):
        tol = float(_num(rest.pop(0), "uniquetol").reshape(-1)[0])
    byrows, datascale, outall = False, None, False
    for i in range(0, len(rest) - 1, 2):
        k = rest[i].text.lower() if _is_text(rest[i]) else ""
        val = rest[i + 1]
        if k == "byrows":
            byrows = bool(_num(val, "uniquetol").reshape(-1)[0])
        elif k == "datascale":
            datascale = _num(val, "uniquetol").reshape(-1)
        elif k == "outputallindices":
            outall = bool(_num(val, "uniquetol").reshape(-1)[0])
    if a.size == 0:
        return (_out(a.reshape(0, 1) if not byrows else a), _out(np.zeros((0, 1))), _out(np.zeros((0, 1))))[:max(1, nargout)]
    if byrows:
        rows = a
    else:
        rows = a.reshape(-1, 1, order="F")
    fin = rows[np.isfinite(rows)]
    ds = datascale if datascale is not None else (np.max(np.abs(fin)) if fin.size else 1.0)
    ds = np.broadcast_to(np.asarray(ds, float), (rows.shape[1],))
    order = np.lexsort(rows.T[::-1])
    keep, ia, ic = [], [], np.zeros(rows.shape[0], int)
    for idx in order:
        r = rows[idx]
        if np.any(np.isnan(r)):
            keep.append(r)
            ia.append(idx)
            ic[idx] = len(keep)
            continue
        hit = None
        for j, (kr, ki) in enumerate(zip(keep, ia)):
            if np.any(np.isnan(kr)):
                continue
            same = np.all((np.abs(kr - r) <= tol * ds) | (kr == r))
            if same:
                hit = j
                break
        if hit is None:
            keep.append(r)
            ia.append(idx)
            ic[idx] = len(keep)
        else:
            ic[idx] = hit + 1
    c = np.array(keep).reshape(len(keep), rows.shape[1])
    if not byrows:
        c = c.reshape(1, -1) if a.ndim == 2 and a.shape[0] == 1 else c.reshape(-1, 1)
    if single:
        c = c.astype(np.float32)
    outs = (_out(c), _out(np.array(ia, float).reshape(-1, 1) + 1), _out(ic.astype(float).reshape(-1, 1)))
    return outs[:max(1, nargout)]


def _ismembertol(args, *, nargout=1):
    _need(args, 2, "ismembertol")
    a, b = _num(args[0], "ismembertol"), _num(args[1], "ismembertol")
    rest = list(args[2:])
    single = args[0].matlab_class() == "single" or args[1].matlab_class() == "single"
    tol = 1e-4 if single else 1e-12
    if rest and not _is_text(rest[0]):
        tol = float(_num(rest.pop(0), "ismembertol").reshape(-1)[0])
    byrows, datascale = False, None
    for i in range(0, len(rest) - 1, 2):
        k = rest[i].text.lower() if _is_text(rest[i]) else ""
        if k == "byrows":
            byrows = bool(_num(rest[i + 1], "ismembertol").reshape(-1)[0])
        elif k == "datascale":
            datascale = _num(rest[i + 1], "ismembertol").reshape(-1)
    if byrows:
        ar, br = a, b
    else:
        ar, br = a.reshape(-1, 1, order="F"), b.reshape(-1, 1, order="F")
    allv = np.concatenate([ar.reshape(-1), br.reshape(-1)])
    fin = allv[np.isfinite(allv)]
    ds = datascale if datascale is not None else (np.max(np.abs(fin)) if fin.size else 1.0)
    ds = np.broadcast_to(np.asarray(ds, float), (ar.shape[1] if ar.ndim > 1 else 1,))
    lia = np.zeros(ar.shape[0], bool)
    loc = np.zeros(ar.shape[0])
    for i in range(ar.shape[0]):
        for j in range(br.shape[0]):
            if np.all((np.abs(ar[i] - br[j]) <= tol * ds) | (ar[i] == br[j])):
                lia[i], loc[i] = True, j + 1
                break
    shape = a.shape if not byrows else (a.shape[0], 1)
    return (NDArrayValue(lia.reshape(shape, order="F")), _out(loc.reshape(shape, order="F")))[:max(1, nargout)]



_ADD_UNITS = {"day": 1.0, "week": 7.0, "hour": 1 / 24, "minute": 1 / 1440, "second": 1 / 86400,
              "millisecond": 1 / 86400000}


def _add_months(dn, q):
    import datetime

    whole = math.floor(dn)
    frac = dn - whole
    d = datetime.date.fromordinal(int(whole) - 366)
    m = d.year * 12 + d.month - 1 + int(q)
    y, mo = divmod(m, 12)
    last = (datetime.date(y + (mo == 11), (mo + 1) % 12 + 1, 1) - datetime.timedelta(days=1)).day
    return datetime.date(y, mo + 1, min(d.day, last)).toordinal() + 366 + frac


def _addtodate(args, *, nargout=1):
    if len(args) < 3:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if not _is_text(args[2]) or len(args[2].rows) != 1:
        raise _err("addtodate: F must be a single character string.", "MATLAB:addtodate:InvalidDateField")
    unit = args[2].text.lower()
    r, q = _num(args[0], "addtodate"), _num(args[1], "addtodate")
    if r.size != 1 and q.size != 1 and r.size != q.size:
        raise _err("addtodate: R and Q must be the same size or scalars.", "MATLAB:addtodate:InvalidQuantity")
    shape = q.shape if r.size == 1 else r.shape
    rr, qq = np.broadcast_to(r.reshape(-1), (max(r.size, q.size),)), np.broadcast_to(q.reshape(-1), (max(r.size, q.size),))
    if unit in ("year", "month"):
        k = 12 if unit == "year" else 1
        if np.any(qq != np.round(qq)):
            raise _err("addtodate: Q must be an integer for years and months.", "MATLAB:addtodate:NonIntegerQuantity")
        out = np.array([_add_months(float(a), int(b) * k) for a, b in zip(rr, qq)])
    elif unit in _ADD_UNITS:
        out = rr + qq * _ADD_UNITS[unit]
    else:
        raise _err(f"addtodate: Invalid time unit: {args[2].text}", "MATLAB:addtodate:InvalidDateField")
    return (_out(out.reshape(shape)),)

def register(builtins: Dict[str, Callable]) -> None:
    table = {
        "issymmetric": _issymmetric, "ishermitian": _ishermitian, "bandwidth": _bandwidth, "isbanded": _isbanded,
        "isdiag": _tri_pred("isdiag", lambda lo, up: lo == 0 and up == 0),
        "istril": _tri_pred("istril", lambda lo, up: up == 0),
        "istriu": _tri_pred("istriu", lambda lo, up: lo == 0),
        "rescale": _rescale, "rms": _rms,
        "rmse": _pair_metric("rmse", lambda a, b: np.abs(a - b) ** 2, np.sqrt),
        "mape": _pair_metric("mape", lambda a, b: 100 * np.abs((b - a) / b)),
        "cart2pol": _cart2pol, "pol2cart": _pol2cart, "cart2sph": _cart2sph, "sph2cart": _sph2cart,
        "bitcmp": _bitcmp, "bitset": _bitset, "eomday": _eomday,
        "tensorprod": _tensorprod, "isuniform": _isuniform, "vecnorm": _vecnorm,
        "sinpi": _pi_trig("sinpi", _sinpi), "cospi": _pi_trig("cospi", _cospi), "polyarea": _polyarea,
        "pagetranspose": _pagetrans(False), "pagectranspose": _pagetrans(True), "swapbytes": _swapbytes,
        "computer": _computer, "addtodate": _addtodate, "rectint": _rectint, "subspace": _subspace, "uniquetol": _uniquetol,
        "ismembertol": _ismembertol, "datevec": _datevec, "normalize": _normalize, "filesep": _filesep, "pathsep": _pathsep, "erase": _erase,
    }
    for k, v in table.items():
        builtins.setdefault(k, v)
    for k in SINGLE_PROPAGATING:  # MATLAB: single in -> single out
        if k in builtins:
            builtins[k] = _single_propagating(builtins[k])


SINGLE_PROPAGATING = ("median", "corrcoef", "trapz", "cumtrapz", "norm", "conv", "deconv", "filter",
                      "polyval", "polyfit", "interp1")


def _is_single(v):
    try:
        return v.matlab_class() == "single"
    except Exception:
        return False


def _single_propagating(fn):
    def g(args, *, nargout=1):
        outs = fn(args, nargout=nargout)
        if not any(_is_single(a) for a in args):
            return outs
        res = []
        for o in outs:
            if isinstance(o, NDArrayValue):
                b = np.asarray(o.backend_buffer())
                if b.dtype == np.float64:
                    o = NDArrayValue(b.astype(np.float32))
                elif b.dtype == np.complex128:
                    o = NDArrayValue(b.astype(np.complex64))
            res.append(o)
        return tuple(res)
    g.__wrapped__ = fn
    return g
