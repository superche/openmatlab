"""ODE solvers, quadrature and optimisation with options (M3-E3, #627).

ode45 (Dormand-Prince 5(4)) and ode23 (Bogacki-Shampine 3(2)) with MATLAB's
error control: a mixed max-norm with ``threshold = AbsTol/RelTol``, step
accepted when ``err <= RelTol``. ``Refine`` output for ``[t0 tf]`` (4 for ode45,
1 for ode23). A ``tspan`` vector gives output at exactly those points (cubic
Hermite dense output). Also odeset/odeget, optimset/optimget, fminbnd (MATLAB's
golden-section + parabolic Brent), quad (adaptive Simpson), integral2
(iterated adaptive Gauss-Kronrod, y-limits may be functions of x), and
integral 'ArrayValued' (vector Gauss-Kronrod). Other integral calls delegate to
the core implementation.
"""

from __future__ import annotations

from typing import Callable, Dict, List

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _nd(a):
    a = np.asarray(a, dtype=float)
    return NDArrayValue(a.reshape(1, 1) if a.ndim == 0 else a)


def _arr(v):
    return np.asarray(v.backend_buffer(), dtype=float)


def _text(v):
    t = getattr(v, "text", None)
    if t is None and getattr(v, "is_string", False):
        t = str(v.data.flat[0])
    return t


def _callfh(fh, *xs):
    if not hasattr(fh, "call"):
        raise _err("The first input must be a function handle.", "MATLAB:invalidFunctionHandle")
    out = fh.call([_nd(x) for x in xs], nargout=1)
    if not out:
        raise _err("The function returned no value.", "MATLAB:noOutput")
    return np.asarray(out[0].backend_buffer(), dtype=float)


# -- option structs ---------------------------------------------------------------------
ODE_FIELDS = ("AbsTol", "BDF", "Events", "InitialStep", "Jacobian", "JConstant", "JPattern", "Mass",
              "MassSingular", "MaxOrder", "MaxStep", "NonNegative", "NormControl", "OutputFcn", "OutputSel",
              "Refine", "RelTol", "Stats", "Vectorized", "MStateDependence", "MvPattern", "InitialSlope")
OPT_FIELDS = ("Display", "MaxFunEvals", "MaxIter", "TolFun", "TolX", "FunValCheck", "OutputFcn", "PlotFcns")


def _setter(fname, fields):
    def fn(args, *, nargout=1):
        from openmatlab.runtime.struct_value import StructValue

        empty = NDArrayValue(np.zeros((0, 0)))
        vals = {f: empty for f in fields}
        args = list(args)
        while args and getattr(args[0], "is_struct", False):
            old = args.pop(0)
            for f in old.fields:
                canon = next((c for c in fields if c.lower() == f.lower()), f)
                v = old.get(f)
                if not (getattr(v, "numel", None) and v.numel() == 0 and not hasattr(v, "text")):
                    vals[canon] = v
        if len(args) % 2:
            raise _err("Arguments must occur in name-value pairs.", f"MATLAB:{fname}:NoValueForProp")
        for k in range(0, len(args), 2):
            name = _text(args[k])
            if name is None:
                raise _err("Expected argument to be a string property name.", f"MATLAB:{fname}:NoPropName")
            hits = [c for c in fields if c.lower() == name.lower()] or [c for c in fields if c.lower().startswith(name.lower())]
            if len(hits) != 1:
                raise _err(f"Unrecognized property name '{name}'.", f"MATLAB:{fname}:InvalidPropName")
            vals[hits[0]] = args[k + 1]
        return [StructValue.scalar([(f, vals[f]) for f in fields] + [(f, v) for f, v in vals.items() if f not in fields])]

    return fn


def _getter(fname):
    def fn(args, *, nargout=1):
        s, name = args[0], _text(args[1])
        default = args[2] if len(args) > 2 else NDArrayValue(np.zeros((0, 0)))
        if getattr(s, "is_struct", False):
            for f in s.fields:
                if f.lower() == name.lower():
                    v = s.get(f)
                    if getattr(v, "numel", None) and v.numel() == 0 and not hasattr(v, "text"):
                        return [default]
                    return [v]
        return [default]

    return fn


def _opt(s, name, default):
    if s is None or not getattr(s, "is_struct", False):
        return default
    for f in s.fields:
        if f.lower() == name.lower():
            v = s.get(f)
            if getattr(v, "numel", None) and v.numel() == 0 and not hasattr(v, "text"):
                return default
            t = _text(v)
            if t is not None:
                return t
            a = _arr(v).reshape(-1)
            return a if a.size > 1 else float(a[0])
    return default


# -- ODE solvers ---------------------------------------------------------------------------
_DP = dict(
    c=np.array([0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1, 1]),
    a=[[], [1 / 5], [3 / 40, 9 / 40], [44 / 45, -56 / 15, 32 / 9],
       [19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729],
       [9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656],
       [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84]],
    b=np.array([35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0]),
    e=np.array([71 / 57600, 0, -71 / 16695, 71 / 1920, -17253 / 339200, 22 / 525, -1 / 40]),
    order=5, refine=4,
)
_BS = dict(
    c=np.array([0, 1 / 2, 3 / 4, 1]),
    a=[[], [1 / 2], [0, 3 / 4], [2 / 9, 1 / 3, 4 / 9]],
    b=np.array([2 / 9, 1 / 3, 4 / 9, 0]),
    e=np.array([-5 / 72, 1 / 12, 1 / 9, -1 / 8]),
    order=3, refine=1,
)


def _hermite(t0, y0, f0, t1, y1, f1, t):
    h = t1 - t0
    s = (t - t0) / h
    h00, h10 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s
    h01, h11 = -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    return h00 * y0 + h10 * h * f0 + h01 * y1 + h11 * h * f1


def _solver(name, tab):
    def fn(args, *, nargout=2):
        if len(args) < 3:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        fh = args[0]
        tspan = _arr(args[1]).reshape(-1)
        y0 = _arr(args[2]).reshape(-1)
        opts = args[3] if len(args) > 3 else None
        if tspan.size < 2:
            raise _err("The time vector TSPAN must have at least two elements.", f"MATLAB:{name}:TspanLength")
        if tspan[0] == tspan[-1]:
            raise _err("The last entry in tspan must be different from the first entry.", "MATLAB:odearguments:TspanEndpointsNotDistinct")
        rtol = float(_opt(opts, "RelTol", 1e-3))
        atol = np.asarray(_opt(opts, "AbsTol", 1e-6), dtype=float)
        if rtol < 100 * np.finfo(float).eps:
            rtol = 100 * np.finfo(float).eps
        refine = int(_opt(opts, "Refine", tab["refine"]))
        t0, tf = float(tspan[0]), float(tspan[-1])
        direction = np.sign(tf - t0)
        maxstep = float(_opt(opts, "MaxStep", 0.1 * abs(tf - t0)))
        n = y0.size

        def f(t, y):
            r = _callfh(fh, np.array([[t]]), y.reshape(-1, 1)).reshape(-1)
            if r.size != n:
                raise _err(f"{name}: the ODE function must return a column vector of length {n}.",
                           "MATLAB:odearguments:SizeIC")
            return r

        thresh = atol / rtol
        y, t = y0.astype(float), t0
        fy = f(t, y)
        h = float(_opt(opts, "InitialStep", 0.0))
        if h <= 0:  # MATLAB's initial step heuristic
            rh = np.max(np.abs(fy) / np.maximum(np.abs(y), thresh)) / (0.8 * rtol ** (1 / tab["order"]))
            h = min(maxstep, abs(tf - t0))
            if h * rh > 1:
                h = 1 / rh
            h = max(h, 16 * np.finfo(float).eps * abs(t))
        T: List[float] = [t0]
        Y: List[np.ndarray] = [y.copy()]
        out_pts = tspan[1:] if tspan.size > 2 else None
        oi = 0
        c, A, b, e = tab["c"], tab["a"], tab["b"], tab["e"]
        steps = 0
        while direction * (tf - t) > 0:
            steps += 1
            if steps > 200000:
                raise _err(f"{name}: too many steps.", f"MATLAB:{name}:TooManySteps")
            h = min(h, maxstep, abs(tf - t))
            if 1.1 * h >= abs(tf - t):
                h = abs(tf - t)
            hs = direction * h
            K = [fy]
            for i in range(1, len(c)):
                yi = y + hs * sum(A[i][j] * K[j] for j in range(i))
                K.append(f(t + c[i] * hs, yi))
            ynew = y + hs * sum(b[j] * K[j] for j in range(len(b)) if b[j])
            fnew = f(t + hs, ynew)
            if len(K) == len(e):
                K[-1] = fnew
            else:
                K.append(fnew)
            est = hs * sum(e[j] * K[j] for j in range(len(e)))
            scale = np.maximum(np.maximum(np.abs(y), np.abs(ynew)), thresh)
            err = float(np.max(np.abs(est) / scale)) if n else 0.0
            if err <= rtol:
                tnew = t + hs
                if out_pts is None:
                    for k in range(1, refine):
                        tk = t + hs * k / refine
                        T.append(tk)
                        Y.append(_hermite(t, y, fy, tnew, ynew, fnew, tk))
                    T.append(tnew)
                    Y.append(ynew)
                else:
                    while oi < out_pts.size and direction * (out_pts[oi] - tnew) <= 0:
                        tk = float(out_pts[oi])
                        T.append(tk)
                        Y.append(ynew.copy() if tk == tnew else _hermite(t, y, fy, tnew, ynew, fnew, tk))
                        oi += 1
                t, y, fy = tnew, ynew, fnew
                fac = 5.0 if err == 0 else min(5.0, 0.8 * (rtol / err) ** (1 / tab["order"]))
                h = h * max(fac, 0.2)
            else:
                h = h * max(0.1, 0.8 * (rtol / err) ** (1 / tab["order"]))
                if h < 16 * np.finfo(float).eps * abs(t):
                    raise _err(f"Unable to meet integration tolerances without reducing the step size below "
                               f"the smallest value allowed at time t.", f"MATLAB:{name}:IntegrationTolNotMet")
        if out_pts is not None:
            T[-1] = float(tspan[-1])
        tt = np.array(T).reshape(-1, 1)
        yy = np.array(Y).reshape(len(Y), n)
        if nargout <= 1:
            from openmatlab.runtime.char_value import CharValue
            from openmatlab.runtime.struct_value import StructValue

            return [StructValue.scalar([("solver", CharValue(name)), ("x", _nd(tt.T)), ("y", _nd(yy.T))])]
        return [_nd(tt), _nd(yy)]

    return fn


# -- quadrature --------------------------------------------------------------------------
_XGK = np.array([0.991455371120813, 0.949107912342759, 0.864864423359769, 0.741531185599394,
                 0.586087235467691, 0.405845151377397, 0.207784955007898, 0.0])
_WGK = np.array([0.022935322010529, 0.063092092629979, 0.104790010322250, 0.140653259715525,
                 0.169004726639267, 0.190350578064785, 0.204432940075298, 0.209482141084728])
_WG = np.array([0.129484966168870, 0.279705391489277, 0.381830050505119, 0.417959183673469])
_NODES = np.concatenate([-_XGK[:-1], _XGK[::-1]])
_WK = np.concatenate([_WGK[:-1], _WGK[::-1]])
_GI = [1, 3, 5, 7, 9, 11, 13]
_WGF = np.array([_WG[0], _WG[1], _WG[2], _WG[3], _WG[2], _WG[1], _WG[0]])


def gk_adapt(func, a, b, abstol=1e-10, reltol=1e-6, vector=False):
    """Adaptive G7-K15. func(xs) -> (len(xs),) or (len(xs), m) when vector."""
    sign = 1.0
    if a > b:
        a, b, sign = b, a, -1.0
    if a == b:
        return 0.0 * np.asarray(func(np.array([a]))[0]) if vector else 0.0
    if np.isinf(a) or np.isinf(b):
        g0 = func

        def func(t, g0=g0):
            x = t / (1 - t ** 2)
            w = (1 + t ** 2) / (1 - t ** 2) ** 2
            v = np.asarray(g0(x))
            return v * (w[:, None] if v.ndim == 2 else w)

        def tmap(x):
            return 0.0 if x == 0 else x / (0.5 + np.sqrt(0.25 + x * x))

        a = -1.0 + 1e-12 if np.isinf(a) else tmap(a)
        b = 1.0 - 1e-12 if np.isinf(b) else tmap(b)
    A, B = a, b

    def seg(lo, hi):
        c, h = (lo + hi) / 2, (hi - lo) / 2
        fx = np.asarray(func(c + h * _NODES), dtype=float)
        k = h * np.tensordot(_WK, fx, axes=(0, 0))
        g = h * np.tensordot(_WGF, fx[_GI], axes=(0, 0))
        return k, float(np.max(np.abs(k - g)))

    total, pending, evals = 0.0, [(A, B) + seg(A, B)], 0
    while pending and evals < 20000:
        lo, hi, val, err = pending.pop()
        evals += 1
        if err <= max(abstol, reltol * float(np.max(np.abs(val)))) * (hi - lo) / (B - A) or (hi - lo) < 1e-12 * (B - A):
            total = total + val
            continue
        mid = (lo + hi) / 2
        pending.append((lo, mid) + seg(lo, mid))
        pending.append((mid, hi) + seg(mid, hi))
    for p in pending:
        total = total + p[2]
    return sign * total


def _wrap_integral(core):
    def fn(args, *, nargout=1):
        names = [(_text(a) or "").lower() for a in args[3::2]]
        if "arrayvalued" not in names:
            return core(args, nargout=nargout)
        opts = {}
        for k in range(3, len(args) - 1, 2):
            opts[_text(args[k]).lower()] = args[k + 1]
        if not bool(np.all(_arr(opts["arrayvalued"]))):
            rest = [x for k, x in enumerate(args) if not (k >= 3 and (k - 3) % 2 == 0 and _text(x).lower() == "arrayvalued")
                    and not (k >= 4 and (k - 4) % 2 == 0 and (_text(args[k - 1]) or "").lower() == "arrayvalued")]
            return core(rest, nargout=nargout)
        fh = args[0]
        a, b = float(_arr(args[1]).reshape(-1)[0]), float(_arr(args[2]).reshape(-1)[0])
        abstol = float(_arr(opts["abstol"]).reshape(-1)[0]) if "abstol" in opts else 1e-10
        reltol = float(_arr(opts["reltol"]).reshape(-1)[0]) if "reltol" in opts else 1e-6
        shape = None

        def func(xs):
            nonlocal shape
            rows = []
            for x in xs:
                r = _callfh(fh, np.array([[x]]))
                shape = r.shape
                rows.append(r.reshape(-1))
            return np.array(rows)

        val = gk_adapt(func, a, b, abstol, reltol, vector=True)
        return [_nd(np.asarray(val).reshape(shape))]

    return fn


def _limit(v):
    if hasattr(v, "call"):
        return lambda x: float(_callfh(v, np.array([[x]])).reshape(-1)[0])
    c = float(_arr(v).reshape(-1)[0])
    return lambda x: c


def _integral2(args, *, nargout=1):
    if len(args) < 5:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    fh = args[0]
    xa, xb = float(_arr(args[1]).reshape(-1)[0]), float(_arr(args[2]).reshape(-1)[0])
    ya, yb = _limit(args[3]), _limit(args[4])
    opts = {(_text(args[k]) or "").lower(): args[k + 1] for k in range(5, len(args) - 1, 2)}
    abstol = float(_arr(opts["abstol"]).reshape(-1)[0]) if "abstol" in opts else 1e-10
    reltol = float(_arr(opts["reltol"]).reshape(-1)[0]) if "reltol" in opts else 1e-6

    def inner(x):
        def g(ys):
            r = _callfh(fh, np.full((1, ys.size), x), ys.reshape(1, -1)).reshape(-1)
            if r.size != ys.size:
                raise _err("Integrand output size does not match the input size.", "MATLAB:integral2:funSizeMismatch")
            return r
        return gk_adapt(g, ya(x), yb(x), abstol, reltol)

    val = gk_adapt(lambda xs: np.array([inner(x) for x in xs]), xa, xb, abstol, reltol)
    return [_nd(val)]


def _quad(args, *, nargout=1):
    fh = args[0]
    a, b = float(_arr(args[1]).reshape(-1)[0]), float(_arr(args[2]).reshape(-1)[0])
    tol = float(_arr(args[3]).reshape(-1)[0]) if len(args) > 3 and _arr(args[3]).size else 1e-6
    count = [0]

    def f(x):
        count[0] += np.size(x)
        r = _callfh(fh, np.asarray(x, dtype=float).reshape(1, -1)).reshape(-1)
        return r

    def simpson(a, b, fa, fm, fb):
        return (b - a) / 6 * (fa + 4 * fm + fb)

    def rec(a, b, fa, fm, fb, whole, tol, depth):
        m = (a + b) / 2
        lm, rm = (a + m) / 2, (m + b) / 2
        flm, frm = f(np.array([lm, rm]))
        left, right = simpson(a, m, fa, flm, fm), simpson(m, b, fm, frm, fb)
        if depth > 50 or abs(left + right - whole) <= 15 * tol:
            return left + right + (left + right - whole) / 15
        return rec(a, m, fa, flm, fm, left, tol / 2, depth + 1) + rec(m, b, fm, frm, fb, right, tol / 2, depth + 1)

    fa, fm, fb = f(np.array([a, (a + b) / 2, b]))
    q = rec(a, b, fa, fm, fb, simpson(a, b, fa, fm, fb), tol, 0)
    return [_nd(q), _nd(float(count[0]))][:max(1, nargout)]


def _fminbnd(args, *, nargout=1):
    """MATLAB fminbnd: golden-section search with parabolic interpolation (Brent)."""
    fh = args[0]
    ax, bx = float(_arr(args[1]).reshape(-1)[0]), float(_arr(args[2]).reshape(-1)[0])
    opts = args[3] if len(args) > 3 else None
    if ax > bx:
        raise _err("The lower bound exceeds the upper bound.", "MATLAB:fminbnd:LowerBoundExceedsUpperBound")
    tol = float(_opt(opts, "TolX", 1e-4))
    maxit = int(_opt(opts, "MaxIter", 500))
    f = lambda x: float(_callfh(fh, np.array([[x]])).reshape(-1)[0])  # noqa: E731
    seps = np.sqrt(np.finfo(float).eps)
    c = 0.5 * (3.0 - np.sqrt(5.0))
    a, b = ax, bx
    v = a + c * (b - a)
    w = xf = v
    e = d = 0.0
    fv = fw = fx = f(xf)
    funccount, it = 1, 0
    xm = 0.5 * (a + b)
    tol1 = seps * abs(xf) + tol / 3.0
    tol2 = 2.0 * tol1
    while abs(xf - xm) > (tol2 - 0.5 * (b - a)):
        gs = True
        if abs(e) > tol1:
            gs = False
            r = (xf - w) * (fx - fv)
            q = (xf - v) * (fx - fw)
            p = (xf - v) * q - (xf - w) * r
            q = 2.0 * (q - r)
            if q > 0.0:
                p = -p
            q = abs(q)
            r, e = e, d
            if abs(p) < abs(0.5 * q * r) and p > q * (a - xf) and p < q * (b - xf):
                d = p / q
                x = xf + d
                if (x - a) < tol2 or (b - x) < tol2:
                    d = tol1 * (np.sign(xm - xf) or 1.0)
            else:
                gs = True
        if gs:
            e = (a - xf) if xf >= xm else (b - xf)
            d = c * e
        x = xf + ((np.sign(d) or 1.0) * max(abs(d), tol1))
        fu = f(x)
        funccount += 1
        it += 1
        if fu <= fx:
            if x >= xf:
                a = xf
            else:
                b = xf
            v, fv, w, fw, xf, fx = w, fw, xf, fx, x, fu
        else:
            if x < xf:
                a = x
            else:
                b = x
            if fu <= fw or w == xf:
                v, fv, w, fw = w, fw, x, fu
            elif fu <= fv or v == xf or v == w:
                v, fv = x, fu
        xm = 0.5 * (a + b)
        tol1 = seps * abs(xf) + tol / 3.0
        tol2 = 2.0 * tol1
        if it >= maxit:
            break
    flag = 1.0 if it < maxit else 0.0
    return [_nd(xf), _nd(fx), _nd(flag)][:max(1, nargout)]


def register(builtins: Dict[str, Callable]) -> None:
    builtins["ode45"] = _solver("ode45", _DP)
    builtins["ode23"] = _solver("ode23", _BS)
    builtins["odeset"] = _setter("odeset", ODE_FIELDS)
    builtins["odeget"] = _getter("odeget")
    builtins["optimset"] = _setter("optimset", OPT_FIELDS)
    builtins["optimget"] = _getter("optimget")
    builtins["fminbnd"] = _fminbnd
    builtins["quad"] = _quad
    builtins["integral2"] = _integral2
    if "integral" in builtins:
        builtins["integral"] = _wrap_integral(builtins["integral"])
