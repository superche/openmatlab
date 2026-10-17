"""Splines, piecewise polynomials, 2-D interpolation and polynomial calculus (M3-E2, #626).

spline (not-a-knot / clamped, MATLAB spline.m end conditions), pchip (Fritsch-Carlson,
MATLAB pchipslopes), ppval/mkpp/unmkpp, interp1 'spline'/'pchip'/'cubic' (delegating
other methods to the core interp1), interp2 linear/nearest, polyder (incl. product and
quotient forms), polyint.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _a(v):
    return np.asarray(v.backend_buffer()).astype(float)


def _row(a):
    return np.asarray(a, dtype=float).reshape(-1)


def _out(a):
    a = np.asarray(a, dtype=float)
    return NDArrayValue(a.reshape(1, 1) if a.ndim == 0 else a)


def _text(v):
    t = getattr(v, "text", None)
    if t is None and getattr(v, "is_string", False):
        t = str(v.data.flat[0])
    return t


def _sites(x, y, fn):
    x, y = _row(x), _row(y)
    if x.size < 2:
        raise _err("There should be at least two data points.", f"MATLAB:{fn}:NotEnoughPts")
    if np.any(np.diff(x) <= 0):
        o = np.argsort(x, kind="stable")
        if np.any(np.diff(x[o]) == 0):
            raise _err("The data sites should be distinct.", f"MATLAB:{fn}:RepeatedSites")
        x = x[o]
        if y.size == x.size:
            y = y[o]
    return x, y


def _hermite(x, y, s):
    h = np.diff(x)
    d = np.diff(y) / h
    c3 = s[:-1]
    c2 = (3 * d - 2 * s[:-1] - s[1:]) / h
    c1 = (s[:-1] + s[1:] - 2 * d) / h ** 2
    return np.column_stack([c1, c2, c3, y[:-1]])


def spline_coefs(x, y):
    n = x.size
    clamped = y.size == n + 2
    if not clamped and y.size != n:
        raise _err("The number of sites, " f"{n}, is incompatible with the number of values, {y.size}.",
                   "MATLAB:spline:XYLengthMismatch")
    ends = (y[0], y[-1]) if clamped else None
    if clamped:
        y = y[1:-1]
    h = np.diff(x)
    d = np.diff(y) / h
    if n == 2 and not clamped:
        return np.column_stack([[0.0], [0.0], d, y[:1]])
    if n == 3 and not clamped:  # not-a-knot on 3 points: the interpolating parabola
        c = np.polyfit(x - x[0], y, 2)
        s = np.array([np.polyval(np.polyder(c), xi - x[0]) for xi in x])
        return _hermite(x, y, s)
    A = np.zeros((n, n))
    r = np.zeros(n)
    for i in range(1, n - 1):
        A[i, i - 1], A[i, i], A[i, i + 1] = h[i], 2 * (h[i - 1] + h[i]), h[i - 1]
        r[i] = 3 * (h[i] * d[i - 1] + h[i - 1] * d[i])
    if clamped:
        A[0, 0] = A[-1, -1] = 1.0
        r[0], r[-1] = ends
    else:
        x0 = h[1] + h[0]
        A[0, 0], A[0, 1] = h[1], x0
        r[0] = ((h[0] + 2 * x0) * h[1] * d[0] + h[0] ** 2 * d[1]) / x0
        xn = h[-1] + h[-2]
        A[-1, -2], A[-1, -1] = xn, h[-2]
        r[-1] = (h[-1] ** 2 * d[-2] + (2 * xn + h[-1]) * h[-2] * d[-1]) / xn
    return _hermite(x, y, np.linalg.solve(A, r))


def pchip_coefs(x, y):
    if y.size != x.size:
        raise _err("The number of sites and values must match.", "MATLAB:pchip:XYLengthMismatch")
    h = np.diff(x)
    d = np.diff(y) / h
    n = x.size
    s = np.zeros(n)
    if n == 2:
        s[:] = d[0]
        return _hermite(x, y, s)
    for k in range(1, n - 1):
        if d[k - 1] * d[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            s[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])

    def end(h0, h1, d0, d1):
        v = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if np.sign(v) != np.sign(d0):
            v = 0.0
        elif np.sign(d0) != np.sign(d1) and abs(v) > abs(3 * d0):
            v = 3 * d0
        return v

    s[0] = end(h[0], h[1], d[0], d[1])
    s[-1] = end(h[-1], h[-2], d[-1], d[-2])
    return _hermite(x, y, s)


def ppeval(breaks, coefs, q):
    q = np.asarray(q, dtype=float)
    flat = q.reshape(-1)
    idx = np.clip(np.searchsorted(breaks, flat, side="right") - 1, 0, coefs.shape[0] - 1)
    t = flat - breaks[idx]
    r = np.zeros_like(flat)
    for j in range(coefs.shape[1]):
        r = r * t + coefs[idx, j]
    r = np.where(np.isnan(flat), np.nan, r)
    return r.reshape(q.shape)


def _pp_struct(breaks, coefs):
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.struct_value import StructValue

    return StructValue.scalar([
        ("form", CharValue("pp")), ("breaks", _out(breaks.reshape(1, -1))), ("coefs", _out(coefs)),
        ("pieces", _out(float(coefs.shape[0]))), ("order", _out(float(coefs.shape[1]))), ("dim", _out(1.0)),
    ])


def _pp_parts(v):
    if not getattr(v, "is_struct", False):
        raise _err("The first input must be a piecewise polynomial structure.", "MATLAB:ppval:InvalidPP")
    try:
        return _row(_a(v.get("breaks"))), np.atleast_2d(_a(v.get("coefs")))
    except Exception:
        raise _err("The first input must be a piecewise polynomial structure.", "MATLAB:ppval:InvalidPP") from None


def _fit(kind):
    def fn(args, *, nargout=1):
        if len(args) < 2:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        x, y = _sites(_a(args[0]), _a(args[1]), kind)
        coefs = spline_coefs(x, y) if kind == "spline" else pchip_coefs(x, y)
        if len(args) == 2:
            return [_pp_struct(x, coefs)]
        q = _a(args[2])
        return [_out(ppeval(x, coefs, q))]

    return fn


def _ppval(args, *, nargout=1):
    pp, xx = args[0], args[1]
    if not getattr(pp, "is_struct", False) and getattr(xx, "is_struct", False):
        pp, xx = xx, pp
    b, c = _pp_parts(pp)
    return [_out(ppeval(b, c, _a(xx)))]


def _mkpp(args, *, nargout=1):
    b = _row(_a(args[0]))
    c = _a(args[1])
    pieces = b.size - 1
    c = c.reshape(pieces, -1) if c.size % max(pieces, 1) == 0 else c
    return [_pp_struct(b, c)]


def _unmkpp(args, *, nargout=1):
    b, c = _pp_parts(args[0])
    return [_out(b.reshape(1, -1)), _out(c), _out(float(c.shape[0])), _out(float(c.shape[1])), _out(1.0)][:max(1, nargout)]


METHODS = ("linear", "nearest", "next", "previous", "pchip", "cubic", "spline", "makima", "v5cubic")


def makima_coefs(x, y):
    h = np.diff(x)
    d = np.diff(y) / h
    n = x.size
    if n == 2:
        return _hermite(x, y, np.full(2, d[0]))
    de = np.concatenate([[3 * d[0] - 2 * d[1], 2 * d[0] - d[1]], d, [2 * d[-1] - d[-2], 3 * d[-1] - 2 * d[-2]]])
    s = np.empty(n)
    for i in range(n):  # slope at x_i uses de[i .. i+3] (two extended deltas each side)
        dm2, dm1, d0, d1 = de[i], de[i + 1], de[i + 2], de[i + 3]
        w1 = abs(d1 - d0) + abs(d1 + d0) / 2
        w2 = abs(dm1 - dm2) + abs(dm1 + dm2) / 2
        s[i] = (dm1 + d0) / 2 if w1 + w2 == 0 else (w1 * dm1 + w2 * d0) / (w1 + w2)
    return _hermite(x, y, s)


def _coefs(method, x, y):
    if method == "spline":
        return spline_coefs(x, y)
    if method == "makima":
        return makima_coefs(x, y)
    return pchip_coefs(x, y)


def _interp_col(method, x, y, q, extrap):
    """One real column y(x) at query points q (flat); out-of-range entries are handled by the caller
    unless ``extrap``."""
    n = x.size
    if method in ("pchip", "cubic", "v5cubic", "spline", "makima"):
        if n < 2:
            raise _err("There should be at least two data points.", "MATLAB:interp1:NotEnoughPts")
        return ppeval(x, _coefs("pchip" if method in ("cubic", "v5cubic") else method, x, y), q)
    if method == "linear":
        i = np.clip(np.searchsorted(x, q, side="right") - 1, 0, n - 2)
        t = (q - x[i]) / (x[i + 1] - x[i])
        r = y[i] + t * (y[i + 1] - y[i])
        return np.where(q == x[i + 1], y[i + 1], r)
    if method == "nearest":
        i = np.clip(np.searchsorted(x, q), 1, n - 1)
        return y[np.where(q - x[i - 1] < x[i] - q, i - 1, i)]  # ties round up (MATLAB)
    if method == "previous":
        i = np.searchsorted(x, q, side="right") - 1
        return np.where(i >= 0, y[np.clip(i, 0, n - 1)], y[0] if extrap else np.nan)
    i = np.searchsorted(x, q, side="left")  # next
    return np.where(i < n, y[np.clip(i, 0, n - 1)], y[-1] if extrap else np.nan)


def _pp_linear_like(method, x, y):
    if method == "linear":
        return x, np.column_stack([np.diff(y) / np.diff(x), y[:-1]])
    if method == "nearest":
        mid = (x[:-1] + x[1:]) / 2
        return np.concatenate([[x[0]], mid, [x[-1]]]), y.reshape(-1, 1)
    if method == "previous":
        return x, y[:-1].reshape(-1, 1)
    return x, y[1:].reshape(-1, 1)


def _interp1(args, *, nargout=1):
    """interp1 (MATLAB documented behaviour): vector or matrix V (interpolated along columns), methods
    linear/nearest/next/previous/pchip/cubic/spline/makima, 'extrap' or a scalar extrapolation value,
    and the legacy pp = interp1(x, v, method, 'pp') form."""
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    first_text = next((k for k, a in enumerate(args) if _text(a) is not None), len(args))
    data, tail = list(args[:first_text]), list(args[first_text:])
    method, extrap, ppform, extrapval = "linear", None, False, None
    for a in tail:
        t = _text(a)
        if t is None:
            extrapval = a
            continue
        t = t.lower().lstrip("*")
        if t in METHODS:
            method = t
        elif t == "extrap":
            extrap = True
        elif t == "pp":
            ppform = True
        else:
            raise _err(f"interp1: invalid method '{_text(a)}'.", "MATLAB:interp1:InvalidMethod")
    if extrapval is not None:
        ev = np.asarray(extrapval.backend_buffer())
        if ev.size != 1:
            raise _err("Extrapolation value must be a scalar.", "MATLAB:interp1:ExtrapNonScalar")
        extrap, extrapval = False, ev.reshape(-1)[0]
    if ppform:
        if len(data) != 2:
            raise _err("Wrong number of input arguments.", "MATLAB:interp1:nargin")
        x, v = _row(_a(data[0])), _row(_a(data[1]))
        o = np.argsort(x, kind="stable")
        x, v = x[o], v[o]
        if method in ("linear", "nearest", "next", "previous"):
            b, c = _pp_linear_like(method, x, v)
        else:
            b, c = x, _coefs("pchip" if method in ("cubic", "v5cubic") else method, x, v)
        return [_pp_struct(b, c)]
    if len(data) == 2:
        V, Xq = np.asarray(data[0].backend_buffer()), np.asarray(data[1].backend_buffer())
        vec = V.ndim == 2 and min(V.shape) == 1
        x = np.arange(1.0, (V.size if vec else V.shape[0]) + 1)
    elif len(data) == 3:
        x = np.asarray(data[0].backend_buffer())
        V, Xq = np.asarray(data[1].backend_buffer()), np.asarray(data[2].backend_buffer())
        if x.ndim > 2 or (x.ndim == 2 and min(x.shape) > 1):
            raise _err("X must be a vector.", "MATLAB:interp1:Xvector")
        x = x.reshape(-1).astype(float)
        vec = V.ndim == 2 and min(V.shape) == 1 and V.size == x.size
    else:
        raise _err("Wrong number of input arguments.", "MATLAB:interp1:nargin")
    if V.dtype.kind in "biu":
        V = V.astype(float)
    if Xq.dtype.kind not in "fc":
        Xq = Xq.astype(float)
    Y = V.reshape(-1, 1) if vec else V.reshape(V.shape[0], -1, order="F")
    if Y.shape[0] != x.size:
        raise _err("The grid vectors must contain unique points and match Y.", "MATLAB:interp1:YInvalidNumRows")
    if x.size < 2:
        raise _err("There should be at least two data points.", "MATLAB:interp1:NotEnoughPts")
    if np.any(np.isnan(x)):
        raise _err("NaN is not an appropriate value for X.", "MATLAB:interp1:NaNinX")
    o = np.argsort(x, kind="stable")
    x, Y = x[o], Y[o]
    if np.any(np.diff(x) == 0):
        raise _err("The grid vectors must contain unique points.", "MATLAB:griddedInterpolant:NonUniqueCompVecsPtsErrId")
    if extrap is None:
        extrap = method in ("pchip", "cubic", "v5cubic", "spline", "makima") and extrapval is None
    fill = np.nan if extrapval is None else extrapval
    q = np.real(Xq).reshape(-1).astype(float)
    nan_q = np.isnan(q)
    qs = np.where(nan_q, x[0], q)
    out_side = (q < x[0]) | (q > x[-1])
    cplx = np.iscomplexobj(Y) or np.iscomplexobj(fill)
    R = np.empty((q.size, Y.shape[1]), dtype=complex if cplx else float)
    for k in range(Y.shape[1]):
        col = Y[:, k]
        parts = [np.real(col), np.imag(col)] if np.iscomplexobj(col) else [col.astype(float)]
        vals = [_interp_col(method, x, p, qs, extrap) for p in parts]
        r = vals[0] + 1j * vals[1] if len(vals) == 2 else vals[0]
        if method == "linear" and extrap:
            lo, hi = q < x[0], q > x[-1]
            r = np.where(lo, col[0] + (q - x[0]) * (col[1] - col[0]) / (x[1] - x[0]), r)
            r = np.where(hi, col[-1] + (q - x[-1]) * (col[-1] - col[-2]) / (x[-1] - x[-2]), r)
        elif method == "nearest" and extrap:
            r = np.where(q < x[0], col[0], np.where(q > x[-1], col[-1], r))
        if not extrap:
            r = np.where(out_side, fill, r)
        R[:, k] = np.where(nan_q, np.nan, r)
    if vec:
        out = R[:, 0].reshape(Xq.shape)
    else:
        trail = V.shape[1:]
        lead = (q.size,) if Xq.ndim == 2 and min(Xq.shape) == 1 else Xq.shape
        out = R.reshape(lead + tuple(trail), order="F")
    if np.iscomplexobj(out) and not np.any(np.imag(out)) and not np.iscomplexobj(V):
        out = out.real
    return [NDArrayValue(np.ascontiguousarray(out)) if out.ndim >= 2 else NDArrayValue(out.reshape(1, -1))]


def _axis(v):
    a = _a(v)
    if a.ndim == 2 and min(a.shape) > 1:
        return a
    return _row(a)


def _interp2(args, *, nargout=1):
    method, extrap = "linear", np.nan
    nums = list(args)
    if nums and _text(nums[-1]) is None and len(nums) in (4, 7) and _text(nums[-2]) is not None:
        extrap = float(_a(nums[-1]).reshape(-1)[0])
        nums = nums[:-1]
    if nums and _text(nums[-1]) is not None:
        method = _text(nums.pop()).lower()
    if len(nums) == 3:
        Z = _a(nums[0])
        xg, yg = np.arange(1, Z.shape[1] + 1, dtype=float), np.arange(1, Z.shape[0] + 1, dtype=float)
        Xq, Yq = _a(nums[1]), _a(nums[2])
    elif len(nums) == 5:
        X, Y, Z = _axis(nums[0]), _axis(nums[1]), _a(nums[2])
        xg = X[0, :] if X.ndim == 2 else X
        yg = Y[:, 0] if Y.ndim == 2 else Y
        Xq, Yq = _a(nums[3]), _a(nums[4])
    else:
        raise _err("Wrong number of input arguments.", "MATLAB:interp2:nargin")
    if Z.shape != (yg.size, xg.size):
        raise _err("The lengths of X and Y must match the size of Z.", "MATLAB:interp2:XYLengthMismatch")
    if Xq.shape != Yq.shape:
        if Xq.size == max(Xq.shape) and Yq.size == max(Yq.shape) and (Xq.shape[0] == 1) and (Yq.ndim == 2 and Yq.shape[1] == 1):
            Xq, Yq = np.meshgrid(_row(Xq), _row(Yq))
        else:
            raise _err("Xq and Yq must be the same size or vectors of different orientations.", "MATLAB:interp2:XqYqMismatch")
    xo, yo = np.argsort(xg), np.argsort(yg)
    xg, yg, Z = xg[xo], yg[yo], Z[np.ix_(yo, xo)]
    xq, yq = Xq.reshape(-1), Yq.reshape(-1)
    out = (xq < xg[0]) | (xq > xg[-1]) | (yq < yg[0]) | (yq > yg[-1]) | np.isnan(xq) | np.isnan(yq)
    if method == "nearest":
        def near(g, q):
            i = np.clip(np.searchsorted(g, q), 1, max(g.size - 1, 1))
            if g.size == 1:
                return np.zeros(q.shape, dtype=int)
            return np.where(q - g[i - 1] < g[i] - q, i - 1, i)
        r = Z[near(yg, np.nan_to_num(yq)), near(xg, np.nan_to_num(xq))]
    elif method == "linear":
        def cell(g, q):
            i = np.clip(np.searchsorted(g, q, side="right") - 1, 0, max(g.size - 2, 0))
            t = (q - g[i]) / (g[i + 1] - g[i]) if g.size > 1 else np.zeros_like(q)
            return i, t
        xs, ys = np.nan_to_num(xq), np.nan_to_num(yq)
        i, tx = cell(xg, xs)
        j, ty = cell(yg, ys)
        i1, j1 = np.minimum(i + 1, xg.size - 1), np.minimum(j + 1, yg.size - 1)
        r = (Z[j, i] * (1 - tx) * (1 - ty) + Z[j, i1] * tx * (1 - ty) + Z[j1, i] * (1 - tx) * ty + Z[j1, i1] * tx * ty)
    else:
        raise _err(f"interp2: method '{method}' is not supported yet.", "MATLAB:interp2:unsupportedMethod")
    r = np.where(out, extrap, r)
    return [_out(r.reshape(Xq.shape))]


def _trim(p):
    p = _row(p)
    nz = np.flatnonzero(p != 0)
    return p[nz[0]:] if nz.size else np.zeros(1)


def _der(p):
    p = _row(p)
    n = p.size - 1
    return _trim(p[:-1] * np.arange(n, 0, -1)) if n > 0 else np.zeros(1)


def _polyder(args, *, nargout=1):
    if len(args) == 1:
        return [_out(_der(_a(args[0])).reshape(1, -1))]
    b, a = _row(_a(args[0])), _row(_a(args[1]))
    if nargout < 2:
        return [_out(_der(np.convolve(b, a)).reshape(1, -1))]
    q = np.polysub(np.convolve(_der(b), a), np.convolve(b, _der(a)))
    return [_out(_trim(q).reshape(1, -1)), _out(_trim(np.convolve(a, a)).reshape(1, -1))]


def _polyint(args, *, nargout=1):
    p = _row(_a(args[0]))
    k = float(_a(args[1]).reshape(-1)[0]) if len(args) > 1 else 0.0
    n = p.size
    return [_out(np.append(p / np.arange(n, 0, -1), k).reshape(1, -1))]


def _poly(args, *, nargout=1):
    a = np.asarray(args[0].backend_buffer())
    if a.ndim == 2 and a.shape[0] == a.shape[1] and a.shape[0] > 1:
        r = np.linalg.eigvals(a.astype(complex))
    else:
        r = a.reshape(-1)
    c = np.poly(r) if r.size else np.ones(1)
    if np.all(np.abs(np.imag(c)) < 1e-12 * max(1.0, float(np.max(np.abs(c))))):
        c = np.real(c)
    return [NDArrayValue(np.asarray(c).reshape(1, -1))]


def register(builtins: Dict[str, Callable]) -> None:
    builtins["spline"] = _fit("spline")
    builtins["pchip"] = _fit("pchip")
    builtins["ppval"] = _ppval
    builtins["mkpp"] = _mkpp
    builtins["unmkpp"] = _unmkpp
    builtins["interp1"] = _interp1
    builtins["interp2"] = _interp2
    builtins["polyder"] = _polyder
    builtins["polyint"] = _polyint
    builtins["poly"] = _poly
