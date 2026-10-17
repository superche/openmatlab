"""Base-MATLAB functions surfaced by the T2 self-check tier (C-E5 #765 burn-down).

Matrix structure: issymmetric ishermitian isdiag istril istriu isbanded bandwidth.
Data: rescale rms rmse mape. Coordinates: cart2pol pol2cart cart2sph sph2cart.
Bits and dates: bitcmp bitset eomday. Paths and text: filesep pathsep erase.

Clean-room implementations from the documented behaviour and standard definitions (NumPy
only); no MATLAB or Octave source was consulted.
"""

from __future__ import annotations

import os
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
        return (_out(a),)
    lo = float(opts["inputmin"].reshape(-1)[0]) if "inputmin" in opts else np.min(a)
    hi = float(opts["inputmax"].reshape(-1)[0]) if "inputmax" in opts else np.max(a)
    x = np.clip(a, lo, hi)
    with np.errstate(invalid="ignore", divide="ignore"):
        if hi == lo:
            r = np.full(a.shape, l)
        else:
            r = l + (x - lo) / (hi - lo) * (u - l)
    return (_out(r),)


def _dim_of(a, args, k):
    if len(args) > k and not _is_text(args[k]):
        d = _num(args[k], "dim").reshape(-1)
        if d.size == 1:
            return int(d[0]) - 1, False
    if len(args) > k and _is_text(args[k]) and args[k].text.lower() == "all":
        return None, True
    nz = [i for i, s in enumerate(a.shape) if s != 1]
    return (nz[0] if nz else 0), False


def _reduce(a, dim, allflag, f):
    if allflag:
        return np.asarray(f(a.reshape(-1, order="F"), 0)).reshape(1, 1)
    if dim >= a.ndim:
        return f(a[..., None], a.ndim)[..., 0] if False else f(np.expand_dims(a, -1), a.ndim)
    return np.expand_dims(f(a, dim), dim)


def _strip_nan(args):
    flag = "includenan"
    rest = []
    for v in args:
        if _is_text(v) and v.text.lower() in ("omitnan", "includenan", "omitmissing", "includemissing"):
            flag = "omitnan" if v.text.lower().startswith("omit") else "includenan"
        else:
            rest.append(v)
    return rest, flag == "omitnan"


def _rms(args, *, nargout=1):
    args, omit = _strip_nan(args)
    _need(args, 1, "rms")
    a = _num(args[0], "rms")
    dim, allf = _dim_of(a, args, 1)
    m = np.nanmean if omit else np.mean
    if a.size == 0 and not allf and dim is not None and a.ndim == 2 and a.shape == (0, 0):
        return (_out(np.array([[np.nan]])),)
    r = _reduce(np.abs(a) ** 2, dim, allf, lambda x, d: m(x, axis=d))
    return (_out(np.sqrt(r)),)


def _pair_metric(fn, f):
    def g(args, *, nargout=1):
        args, omit = _strip_nan(args)
        _need(args, 2, fn)
        a, b = _num(args[0], fn), _num(args[1], fn)
        try:
            d = f(a, b)
        except ValueError:
            raise _err("Arrays have incompatible sizes for this operation.", "MATLAB:sizeDimensionsMustMatch")
        dim, allf = _dim_of(d, args, 2)
        m = np.nanmean if omit else np.mean
        return (_out(g.post(_reduce(d, dim, allf, lambda x, k: m(x, axis=k)))),)
    g.post = (lambda r: np.sqrt(r)) if fn == "rmse" else (lambda r: r)
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


def register(builtins: Dict[str, Callable]) -> None:
    table = {
        "issymmetric": _issymmetric, "ishermitian": _ishermitian, "bandwidth": _bandwidth, "isbanded": _isbanded,
        "isdiag": _tri_pred("isdiag", lambda lo, up: lo == 0 and up == 0),
        "istril": _tri_pred("istril", lambda lo, up: up == 0),
        "istriu": _tri_pred("istriu", lambda lo, up: lo == 0),
        "rescale": _rescale, "rms": _rms,
        "rmse": _pair_metric("rmse", lambda a, b: np.abs(a - b) ** 2),
        "mape": _pair_metric("mape", lambda a, b: 100 * np.abs((a - b) / a)),
        "cart2pol": _cart2pol, "pol2cart": _pol2cart, "cart2sph": _cart2sph, "sph2cart": _sph2cart,
        "bitcmp": _bitcmp, "bitset": _bitset, "eomday": _eomday,
        "filesep": _filesep, "pathsep": _pathsep, "erase": _erase,
    }
    for k, v in table.items():
        builtins.setdefault(k, v)
