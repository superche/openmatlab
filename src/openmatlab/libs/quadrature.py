"""Adaptive quadrature: quadgk, quadl, quadv, quad2d, integral2, integral3, dblquad, triplequad (#765 T2 burn-down).

Clean-room, NumPy only, against the documented MATLAB syntaxes.  One engine serves all of them: global
adaptive cubature over boxes of the unit cube with a tensor-product Gauss-Kronrod pair (G7/K15 in one and
two dimensions, G3/K7 in three).  Every box batch is evaluated in a single vectorised call of the integrand.
Each coordinate is mapped from [0, 1] through the cubic ``s(u) = 3u^2 - 2u^3`` (Shampine's transformation,
which weakens end-point singularities and keeps the nodes off the ends), and then onto the finite, half-
infinite or infinite range; inner limits may be functions of the outer variables.  ``quadgk`` waypoints
(also complex: contour integrals) split the path into straight segments.  ``quadl`` is the adaptive
Gauss-Lobatto rule of Gander and Gautschi (2000), so its evaluation count grows as the tolerance shrinks.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Sequence

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

_XK = np.array([0.991455371120812639, 0.949107912342758525, 0.864864423359769073, 0.741531185599394440,
                0.586087235467691130, 0.405845151377397167, 0.207784955007898468, 0.0])
_WK = np.array([0.022935322010529225, 0.063092092629978553, 0.104790010322250184, 0.140653259715525919,
                0.169004726639267903, 0.190350578064785410, 0.204432940075298892, 0.209482141084727828])
_WG = np.array([0.129484966168869693, 0.279705391489276668, 0.381830050505118945, 0.417959183673469388])
# K15 on [-1, 1]: nodes ascending; Gauss G7 nodes are the odd positions.
K15_X = np.concatenate([-_XK[:-1], _XK[::-1]])
K15_W = np.concatenate([_WK[:-1], _WK[::-1]])
G7_W = np.zeros(15)
G7_W[1::2] = np.concatenate([_WG, _WG[-2::-1]])
# K7 / G3 (Kronrod extension of the 3-point Gauss rule).
K7_X = np.array([-0.960491268708020283, -0.774596669241483377, -0.434243749346802558, 0.0,
                 0.434243749346802558, 0.774596669241483377, 0.960491268708020283])
K7_W = np.array([0.104656226026467265, 0.268488089868333440, 0.401397414775962222, 0.450916538658474142,
                 0.401397414775962222, 0.268488089868333440, 0.104656226026467265])
G3_W = np.array([0.0, 5 / 9, 0.0, 8 / 9, 0.0, 5 / 9, 0.0])


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _warn(msg, ident=""):
    try:
        from openmatlab.libs.error_builtins import emit_warning  # type: ignore

        emit_warning(msg, ident)
    except Exception:  # noqa: BLE001 - a warning must never break the integral
        pass


def _val(a) -> NDArrayValue:
    a = np.asarray(a)
    if a.dtype.kind not in "fc":
        a = a.astype(float)
    return NDArrayValue(a.reshape(1, 1) if a.ndim == 0 else a)


def _arr(v) -> np.ndarray:
    buf = getattr(v, "backend_buffer", None)
    if buf is None:
        raise _err("Expected a numeric value.", "MATLAB:invalidType")
    a = np.asarray(buf())
    return a.astype(float) if a.dtype.kind in "biu" else a


def _text(v):
    t = getattr(v, "text", None)
    if t is None and getattr(v, "is_string", False):
        t = str(v.data.flat[0])
    return t


def _scalar(v, fn, what="limits") -> complex:
    a = _arr(v).reshape(-1)
    if a.size != 1:
        raise _err(f"{fn}: the integration {what} must be scalars.", f"MATLAB:{fn}:invalidLimit")
    return complex(a[0]) if np.iscomplexobj(a) else float(a[0])


def _is_handle(v) -> bool:
    return hasattr(v, "call") and getattr(v, "matlab_class", lambda: "")() == "function_handle"


def _handle(v, fn):
    if not _is_handle(v):
        raise _err(f"{fn}: the integrand must be a function handle.", "MATLAB:invalidFunctionHandle")
    return v


def _call(fh, *xs) -> np.ndarray:
    out = fh.call([_val(x) for x in xs], nargout=1)
    if not out:
        raise _err("The integrand returned no value.", "MATLAB:noOutput")
    return _arr(out[0])


def _opts(args: Sequence, start: int, fn: str, known: Sequence[str]) -> Dict[str, object]:
    if (len(args) - start) % 2:
        raise _err(f"{fn}: options must be given as name-value pairs.", f"MATLAB:{fn}:invalidOptions")
    out = {}
    for k in range(start, len(args), 2):
        name = (_text(args[k]) or "").lower()
        if name not in known:
            raise _err(f"{fn}: unrecognised option '{_text(args[k]) or '?'}'.", f"MATLAB:{fn}:unknownOption")
        out[name] = args[k + 1]
    return out


def _num_opt(opts, name, default) -> float:
    if name not in opts:
        return default
    a = _arr(opts[name]).reshape(-1)
    if a.size != 1 or not np.isfinite(a[0]) or a[0] < 0:
        raise _err(f"The value of '{name}' must be a finite nonnegative scalar.", "MATLAB:InputParser:ArgumentFailedValidation")
    return float(a[0])


def _flag_opt(opts, name, default) -> bool:
    return bool(np.all(_arr(opts[name]))) if name in opts else default


# ---- coordinate maps ---------------------------------------------------------------------------

def _smooth(u):
    return u * u * (3 - 2 * u), 6 * u * (1 - u)


def _map(u, lo, hi):
    """x(u), dx/du for u in (0, 1); lo/hi are scalars or arrays (inner limits), possibly infinite."""
    v, dv = _smooth(u)
    lo_inf = np.isinf(np.real(lo)) if np.ndim(lo) == 0 else None
    hi_inf = np.isinf(np.real(hi)) if np.ndim(hi) == 0 else None
    if lo_inf and hi_inf:
        w = 2 * v - 1
        x = w / (1 - w * w)
        dx = 2 * dv * (1 + w * w) / (1 - w * w) ** 2
        return (x, dx) if np.real(lo) < np.real(hi) else (-x, -dx)
    if hi_inf:
        x = lo + np.sign(np.real(hi)) * v / (1 - v)
        return x, np.sign(np.real(hi)) * dv / (1 - v) ** 2
    if lo_inf:
        x = hi - np.sign(-np.real(lo)) * (1 - v) / v
        return x, np.sign(-np.real(lo)) * dv / (v * v)
    return lo + (hi - lo) * v, (hi - lo) * dv


# ---- the adaptive engine -----------------------------------------------------------------------

class _Rule:
    def __init__(self, x, wk, wg):
        self.u = (np.asarray(x) + 1) / 2  # nodes on [0, 1]
        self.wk, self.wg = np.asarray(wk) / 2, np.asarray(wg) / 2


R15 = _Rule(K15_X, K15_W, G7_W)
R7 = _Rule(K7_X, K7_W, G3_W)


def cubature(integrand: Callable, ndim: int, abstol: float, reltol: float, *, rule=None, init=None,
             max_boxes=650, out_shape=()):
    """Integrate ``integrand(U, *)`` over [0, 1]^ndim.

    ``integrand(U)`` receives the points as an (ndim, npoints) array and returns the transformed
    integrand values with shape out_shape + (npoints,).  Returns (q, errbnd, nevals, converged).
    """
    rule = rule or (R15 if ndim < 3 else R7)
    m = rule.u.size
    grids = np.meshgrid(*([rule.u] * ndim), indexing="ij")
    ref_u = np.stack([g.reshape(-1) for g in grids])  # (ndim, m^ndim)
    wk = np.ones(1)
    wg = np.ones(1)
    for _ in range(ndim):
        wk, wg = np.kron(wk, rule.wk), np.kron(wg, rule.wg)
    del m
    n0 = init if init is not None else (10 if ndim == 1 else 2)
    edges = np.linspace(0, 1, n0 + 1)
    los = [np.array(p) for p in np.meshgrid(*([edges[:-1]] * ndim), indexing="ij")]
    lo = np.stack([g.reshape(-1) for g in los], axis=1)  # (nbox, ndim)
    width = np.full_like(lo, 1.0 / n0)
    done_q, done_e, nevals = 0, 0.0, 0
    q_act = e_act = None

    def evaluate(lo, width):
        pts = lo[:, :, None] + width[:, :, None] * ref_u[None, :, :]  # (nbox, ndim, npt)
        nb, npt = lo.shape[0], ref_u.shape[1]
        vals = np.asarray(integrand(pts.transpose(1, 0, 2).reshape(ndim, nb * npt)))
        vals = vals.reshape(out_shape + (nb, npt))
        vol = np.prod(width, axis=1)
        qk = (vals * wk).sum(-1) * vol
        qg = (vals * wg).sum(-1) * vol
        err = np.abs(qk - qg)
        err = err.reshape(-1, nb).max(axis=0) if out_shape else err
        return qk, err

    q_act, e_act = evaluate(lo, width)
    nevals += lo.shape[0] * ref_u.shape[1]
    converged = False
    while True:
        q = done_q + q_act.sum(-1)
        tol = max(abstol, reltol * float(np.max(np.abs(q))) if np.size(q) else 0.0)
        total_err = done_e + float(e_act.sum())
        if not np.all(np.isfinite(q)):
            break
        if total_err <= tol:
            converged = True
            break
        vol = np.prod(width, axis=1)
        bad = e_act > tol * vol  # boxes whose error exceeds their share
        if not bad.any():
            bad = e_act >= e_act.max()
        keep = ~bad
        done_q = done_q + q_act[..., keep].sum(-1)
        done_e += float(e_act[keep].sum())
        if lo.shape[0] - keep.sum() + bad.sum() * 2 > max_boxes or width[bad].min() < 1e-15:
            q_act, e_act = q_act[..., bad], e_act[bad]
            break
        blo, bw = lo[bad], width[bad]
        dim = np.argmax(bw, axis=1)
        half = bw.copy()
        half[np.arange(bw.shape[0]), dim] /= 2
        lo2 = blo.copy()
        lo2[np.arange(bw.shape[0]), dim] += half[np.arange(bw.shape[0]), dim]
        lo, width = np.concatenate([blo, lo2]), np.concatenate([half, half])
        q_act, e_act = evaluate(lo, width)
        nevals += lo.shape[0] * ref_u.shape[1]
    q = done_q + q_act.sum(-1)
    return q, done_e + float(e_act.sum()), nevals, converged


# ---- one dimension -----------------------------------------------------------------------------

def _path(a, b, waypoints):
    pts = [a] + list(waypoints) + [b]
    return [(pts[i], pts[i + 1]) for i in range(len(pts) - 1) if pts[i] != pts[i + 1]]


def integrate1(f: Callable, a, b, abstol=1e-10, reltol=1e-6, waypoints=(), max_intervals=650, array_shape=None,
               init=None):
    """f(x: 1-D array) -> values (npoints,) or, with array_shape, array_shape + (npoints,)."""
    if a == b and not len(waypoints):
        z = np.zeros(array_shape or ())
        return z, 0.0, 0, True
    segs = _path(a, b, waypoints)
    shape = tuple(array_shape or ())
    nseg = len(segs)

    def integrand(U):
        u = U[0]
        k = np.minimum((u * nseg).astype(int), nseg - 1)
        t = u * nseg - k
        xs = np.empty(u.shape, dtype=complex)
        dxs = np.empty(u.shape, dtype=complex)
        for i, (p, q) in enumerate(segs):
            sel = k == i
            x, dx = _map(t[sel], p, q)
            xs[sel], dxs[sel] = x, dx * nseg
        real = all(np.isreal(p) and np.isreal(q) for p, q in segs)
        x_eval = xs.real if real else xs
        fx = np.asarray(f(x_eval))
        out = fx * (dxs.real if real else dxs)
        out = np.where(dxs == 0, 0, out) if not shape else out
        return out

    init = init if init is not None else max(10, nseg)
    init = int(np.ceil(init / nseg) * nseg)  # segment boundaries fall on box edges
    q, err, nev, ok = cubature(integrand, 1, abstol, reltol, init=init, max_boxes=max(max_intervals, init + 1),
                               out_shape=shape)
    return q, err, nev, ok


def _vec_caller(fh, fn):
    def f(x):
        y = _call(fh, x.reshape(1, -1))
        if y.size != x.size:
            raise _err(f"{fn}: the integrand must return an output the same size as the input (use .* ./ .^).",
                       f"MATLAB:{fn}:FxNotSameSizeAsX")
        return y.reshape(-1)
    return f


def _array_caller(fh, shape_box: List):
    def f(x):
        rows = []
        for xi in x:
            y = _call(fh, np.array([[xi]]))
            if shape_box[0] is None:
                shape_box[0] = y.shape
            rows.append(y.reshape(-1))
        return np.stack(rows, axis=-1)
    return f


def _probe_shape(fh, a, b):
    """Shape of an array-valued integrand (evaluated once at an interior point)."""
    xm = (a + b) / 2 if np.isfinite(np.real(a)) and np.isfinite(np.real(b)) else (
        a + 1 if np.isfinite(np.real(a)) else b - 1 if np.isfinite(np.real(b)) else 0.0)
    return _call(fh, np.array([[xm]])).shape


def _result_class(*limits):
    return np.float32 if any(np.asarray(_arr(v)).dtype == np.float32 for v in limits) else None


def _cast(q, cls):
    q = np.asarray(q)
    if cls is np.float32:
        q = q.astype(np.complex64 if np.iscomplexobj(q) else np.float32)
    if np.iscomplexobj(q) and np.all(q.imag == 0):
        q = q.real
    return q


def _quadgk(args, *, nargout=1, fn="quadgk"):
    if len(args) < 3:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    fh = _handle(args[0], fn)
    a, b = _scalar(args[1], fn), _scalar(args[2], fn)
    opts = _opts(args, 3, fn, ("abstol", "reltol", "waypoints", "maxintervalcount", "arrayvalued", "trace"))
    cls = _result_class(args[1], args[2], *([opts["waypoints"]] if "waypoints" in opts else []))
    abstol = _num_opt(opts, "abstol", 1e-5 if cls is np.float32 else 1e-10)
    reltol = _num_opt(opts, "reltol", 1e-4 if cls is np.float32 else 1e-6)
    maxint = int(_num_opt(opts, "maxintervalcount", 650))
    wp = _arr(opts["waypoints"]).reshape(-1).tolist() if "waypoints" in opts else []
    if wp and (np.isinf(np.real(a)) or np.isinf(np.real(b))):
        raise _err(f"{fn}: waypoints are not allowed with infinite limits.", f"MATLAB:{fn}:invalidWaypoints")
    if _flag_opt(opts, "arrayvalued", False):
        shape = _probe_shape(fh, a, b)
        q, err, _, ok = integrate1(_array_caller(fh, [None]), a, b, abstol, reltol, wp, maxint,
                                   array_shape=(int(np.prod(shape)),))
        q = np.asarray(q).reshape(shape)
    else:
        q, err, _, ok = integrate1(_vec_caller(fh, fn), a, b, abstol, reltol, wp, maxint)
    if not ok:
        _warn(f"Reached the limit on the maximum number of intervals in use. Approximate bound on error is {err:.1e}.",
              f"MATLAB:{fn}:MaxIntervalCountReached")
    return [_val(_cast(q, cls)), _val(_cast(err, cls))][:max(1, nargout)]


def _quadv(args, *, nargout=1):
    """quadv(fun, a, b, tol, trace, p1, ...): vectorised (array-valued) adaptive quadrature."""
    if len(args) < 3:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    fh = _handle(args[0], "quadv")
    a, b = _scalar(args[1], "quadv"), _scalar(args[2], "quadv")
    tol = float(_arr(args[3]).reshape(-1)[0]) if len(args) > 3 and _arr(args[3]).size else 1e-6
    extra = list(args[5:])

    def g(x):
        return _call(fh, x, *[_arr(e) for e in extra]) if not extra else _arr(
            fh.call([_val(x)] + extra, nargout=1)[0])

    class _H:
        def call(self, xs, nargout=1):
            return [_val(g(_arr(xs[0])))]

    shape = _probe_shape(_H(), a, b)
    q, err, nev, ok = integrate1(_array_caller(_H(), [None]), a, b, tol, 0.0, (), 650,
                                 array_shape=(int(np.prod(shape)),))
    cls = _result_class(args[1], args[2])
    return [_val(_cast(np.asarray(q).reshape(shape), cls)), _val(float(nev))][:max(1, nargout)]


# ---- quadl: adaptive Gauss-Lobatto (Gander & Gautschi) -----------------------------------------

def _quadl(args, *, nargout=1):
    if len(args) < 3:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    fh = _handle(args[0], "quadl")
    a, b = _scalar(args[1], "quadl"), _scalar(args[2], "quadl")
    tol = float(_arr(args[3]).reshape(-1)[0]) if len(args) > 3 and _arr(args[3]).size else 1e-6
    extra = list(args[5:])
    count = [0]

    def f(x):
        x = np.asarray(x, dtype=float)
        count[0] += x.size
        y = _arr(fh.call([_val(x.reshape(1, -1))] + extra, nargout=1)[0]).reshape(-1)
        if y.size != x.size:
            raise _err("quadl: the integrand must return an output the same size as the input.",
                       "MATLAB:quadl:FxNotSameSizeAsX")
        return y

    if a == b:
        q = 0.0
    else:
        alpha, beta = np.sqrt(2 / 3), 1 / np.sqrt(5)
        x1, x2, x3 = 0.942882415695480, 0.641853342345781, 0.236383199662150
        m, h = (a + b) / 2, (b - a) / 2
        xs = np.array([a, m - x1 * h, m - alpha * h, m - x2 * h, m - beta * h, m - x3 * h, m,
                       m + x3 * h, m + beta * h, m + x2 * h, m + alpha * h, m + x1 * h, b])
        y = f(xs)
        if not np.isfinite(y[0]):
            y[0] = f(np.array([a + np.finfo(float).eps * (b - a)]))[0]
        if not np.isfinite(y[-1]):
            y[-1] = f(np.array([b - np.finfo(float).eps * (b - a)]))[0]
        i2 = h / 6 * (y[0] + y[12] + 5 * (y[4] + y[8]))
        i1 = h / 1470 * (77 * (y[0] + y[12]) + 432 * (y[2] + y[10]) + 625 * (y[4] + y[8]) + 672 * y[6])
        is_ = h * (0.0158271919734802 * (y[0] + y[12]) + 0.0942738402188500 * (y[1] + y[11])
                   + 0.155071987336585 * (y[2] + y[10]) + 0.188821573960182 * (y[3] + y[9])
                   + 0.199773405226859 * (y[4] + y[8]) + 0.224926465333340 * (y[5] + y[7])
                   + 0.242611071901408 * y[6])
        depth = [0]

        def rec(a, b, fa, fb):
            depth[0] += 1
            h = (b - a) / 2
            m = (a + b) / 2
            mll, ml, mr, mrr = m - alpha * h, m - beta * h, m + beta * h, m + alpha * h
            fmll, fml, fm, fmr, fmrr = f(np.array([mll, ml, m, mr, mrr]))
            i2 = h / 6 * (fa + fb + 5 * (fml + fmr))
            i1 = h / 1470 * (77 * (fa + fb) + 432 * (fmll + fmrr) + 625 * (fml + fmr) + 672 * fm)
            if abs(i1 - i2) <= tol or is_ + (i1 - i2) == is_ or mll <= a or b <= mrr or depth[0] > 10000:
                return i1
            return (rec(a, mll, fa, fmll) + rec(mll, ml, fmll, fml) + rec(ml, m, fml, fm) + rec(m, mr, fm, fmr)
                    + rec(mr, mrr, fmr, fmrr) + rec(mrr, b, fmrr, fb))

        q = rec(a, b, y[0], y[12])
    cls = _result_class(args[1], args[2])
    return [_val(_cast(q, cls)), _val(float(count[0]))][:max(1, nargout)]


# ---- two and three dimensions ------------------------------------------------------------------

def _limit_fn(v, fn):
    """A constant limit or a function handle of the outer variables (vectorised)."""
    if _is_handle(v):
        def g(*outer):
            y = _call(v, *outer)
            return np.broadcast_to(y.reshape(-1) if y.size == outer[0].size else y.reshape(-1)[0], outer[0].shape) \
                if y.size in (1, outer[0].size) else _bad_limit(fn)
        return g, False
    c = _scalar(v, fn)
    return (lambda *outer: c), True


def _bad_limit(fn):
    raise _err(f"{fn}: a limit function must return an array the same size as its input.", f"MATLAB:{fn}:limitSize")


def _nd_integrand(fh, fn, ndim, limits, vectorized=True, extra=()):
    """Integrand on the unit cube for an iterated region x1 in [a, b], x2 in [c(x1), d(x1)], ..."""
    def call(*xs):
        if vectorized:
            y = _arr(fh.call([_val(x.reshape(1, -1)) for x in xs] + list(extra), nargout=1)[0])
            if y.size == xs[0].size:
                return y.reshape(-1)
            if y.size == 1:
                return np.full(xs[0].size, y.reshape(-1)[0])
            raise _err(f"{fn}: the integrand must return an output the same size as its inputs (use .* ./ .^).",
                       f"MATLAB:{fn}:funSizeMismatch")
        return np.array([_arr(fh.call([_val(np.array([[x[k]]])) for x in xs] + list(extra), nargout=1)[0]).reshape(-1)[0]
                         for k in range(xs[0].size)])

    def integrand(U):
        xs, jac = [], np.ones(U.shape[1])
        for d in range(ndim):
            lo_f, hi_f = limits[d]
            lo, hi = lo_f(*xs), hi_f(*xs)
            if np.ndim(lo) or np.ndim(hi):
                lo, hi = np.broadcast_to(lo, U[d].shape), np.broadcast_to(hi, U[d].shape)
            x, dx = _map(U[d], lo, hi)
            xs.append(np.asarray(x, dtype=float))
            jac = jac * dx
        fx = call(*xs)
        return np.where(jac == 0, 0, fx * jac)

    return integrand


def _region_opts(args, start, fn, ndim):
    opts = _opts(args, start, fn, ("abstol", "reltol", "method", "vectorized", "singular", "maxfunevals",
                                   "failureplot"))
    return opts, _num_opt(opts, "abstol", 1e-10), _num_opt(opts, "reltol", 1e-6)


def _integralN(fn, ndim):
    def impl(args, *, nargout=1):
        nlim = 2 * ndim
        if len(args) < 1 + nlim:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        fh = _handle(args[0], fn)
        a, b = _scalar(args[1], fn), _scalar(args[2], fn)
        limits = [((lambda *o: a), (lambda *o: b))]
        for d in range(1, ndim):
            lo, _ = _limit_fn(args[1 + 2 * d], fn)
            hi, _ = _limit_fn(args[2 + 2 * d], fn)
            limits.append((lo, hi))
        opts, abstol, reltol = _region_opts(args, 1 + nlim, fn, ndim)
        vec = _flag_opt(opts, "vectorized", True)
        integrand = _nd_integrand(fh, fn, ndim, limits, vec)
        q, err, _, ok = cubature(integrand, ndim, abstol, reltol, max_boxes=4000 if ndim == 2 else 1500)
        if not ok:
            _warn(f"{fn}: the integral may not meet the tolerances; approximate bound on error is {err:.1e}.",
                  f"MATLAB:{fn}:maxFunEvalsPass")
        cls = _result_class(*args[1:1 + nlim]) if all(not _is_handle(v) for v in args[1:1 + nlim]) else None
        return [_val(_cast(q, cls)), _val(err)][:max(1, nargout)]
    return impl


def _iterated(fn, ndim):
    """dblquad / triplequad: f(x, y[, z]) with x a vector and y, z scalars; tol and method as documented."""
    def impl(args, *, nargout=1):
        nlim = 2 * ndim
        if len(args) < 1 + nlim:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        fh = _handle(args[0], fn)
        lims = [(_scalar(args[1 + 2 * d], fn), _scalar(args[2 + 2 * d], fn)) for d in range(ndim)]
        tol = 1e-6
        if len(args) > 1 + nlim and getattr(args[1 + nlim], "backend_buffer", None) is not None \
                and _arr(args[1 + nlim]).size:
            tol = float(_arr(args[1 + nlim]).reshape(-1)[0])
        extra = list(args[3 + nlim:])

        def inner_x(*outer):
            def f(x):
                y = _arr(fh.call([_val(x.reshape(1, -1))] + [_val(np.array([[o]])) for o in outer] + extra,
                                 nargout=1)[0]).reshape(-1)
                return y if y.size == x.size else np.full(x.size, y[0]) if y.size == 1 else _bad_size(fn)
            q, _, _, _ = integrate1(f, lims[0][0], lims[0][1], tol, 0.0, init=1)
            return float(np.real(q))

        def level(d, outer):
            if d == 0:
                return inner_x(*outer)

            def g(t):
                return np.array([level(d - 1, (float(ti),) + outer) for ti in t])
            q, _, _, _ = integrate1(g, lims[d][0], lims[d][1], tol, 0.0, init=1)
            return float(np.real(q))

        return [_val(level(ndim - 1, ()))]
    return impl


def _bad_size(fn):
    raise _err(f"{fn}: the integrand must return a vector the same size as x.", f"MATLAB:{fn}:funSizeMismatch")


def register(builtins: Dict[str, Callable]) -> None:
    builtins["quadgk"] = _quadgk
    builtins["integral"] = lambda args, *, nargout=1: _quadgk(args, nargout=nargout, fn="integral")
    builtins["quadl"] = _quadl
    builtins["quadv"] = _quadv
    builtins["quad2d"] = _integralN("quad2d", 2)
    builtins["integral2"] = _integralN("integral2", 2)
    builtins["integral3"] = _integralN("integral3", 3)
    builtins["dblquad"] = _iterated("dblquad", 2)
    builtins["triplequad"] = _iterated("triplequad", 3)
