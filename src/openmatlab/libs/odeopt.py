"""ODE solvers, quadrature and optimisation with options (M3-E3, #627).

ode45 (Dormand-Prince 5(4)) and ode23 (Bogacki-Shampine 3(2)) with MATLAB's
error control: a mixed max-norm with ``threshold = AbsTol/RelTol``, step
accepted when ``err <= RelTol``. ``Refine`` output for ``[t0 tf]`` (4 for ode45,
1 for ode23). A ``tspan`` vector gives output at exactly those points (cubic
Hermite dense output). Also odeset/odeget, optimset/optimget, fminbnd (MATLAB's
golden-section + parabolic Brent), quad (adaptive Simpson), integral2
(iterated adaptive Gauss-Kronrod, y-limits may be functions of x), and
integral 'ArrayValued' (vector Gauss-Kronrod). Other integral calls delegate to
the core implementation. ode45 and ode23 apply RelTol, AbsTol, Refine, MaxStep,
and InitialStep. Any other nonempty odeset field is an error before the step
loop (#1085), including a second case spelling and a nonscalar structure.
odeset itself uses that same shape and alias rule when it copies an old
structure, so a later element or an earlier spelling cannot disappear before
the solver sees it. An explicit name-value pair still overwrites, including [].
Every applied option, including InitialStep, is read before the first f(t, y).
Empty defaults are left as they are. Only NormControl, Stats, BDF, Vectorized,
and JConstant accept off.
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


def _legacy_setter(fname, fields, args):
    """optimset path: first case match on element 1. ODE options do not use this."""
    from openmatlab.runtime.struct_value import StructValue

    empty = NDArrayValue(np.zeros((0, 0)))
    vals = {f: empty for f in fields}
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


def _name_value_pairs(fname, fields, args):
    if len(args) % 2:
        raise _err("Arguments must occur in name-value pairs.", f"MATLAB:{fname}:NoValueForProp")
    pairs = []
    for k in range(0, len(args), 2):
        name = _text(args[k])
        if name is None:
            raise _err("Expected argument to be a string property name.", f"MATLAB:{fname}:NoPropName")
        hits = [c for c in fields if c.lower() == name.lower()] or [c for c in fields if c.lower().startswith(name.lower())]
        if len(hits) != 1:
            raise _err(f"Unrecognized property name '{name}'.", f"MATLAB:{fname}:InvalidPropName")
        pairs.append((hits[0], args[k + 1]))
    return pairs


def _absorb_ode_struct(old, vals, overridden):
    """Copy one old structure into ``vals``.

    Shape and alias conflicts use the same helpers as the solver. A zero-element
    structure contributes nothing. A later structure may replace a single kept
    value (documented struct merge). An empty field does not clear a value
    already kept. ``overridden`` names are left for the explicit name-value
    pair, which is how ``odeset(old, 'Events', [])`` clears a handle even when
    the old structure names that option twice.
    """
    scalar = _scalar_option_struct("odeset", old)
    if scalar is None:
        return
    known = {c.lower() for c in ODE_FIELDS}
    for canon in ODE_FIELDS:
        if canon in overridden:
            continue
        v = _distinct_set_value("odeset", scalar, canon)
        if v is not None:
            vals[canon] = v
    for f in scalar.fields:
        if f.lower() in known:
            continue
        v = scalar.get(f)
        if _value_unset(v):
            continue
        vals[f] = v


def _build_odeset(args):
    from openmatlab.runtime.struct_value import StructValue

    empty = NDArrayValue(np.zeros((0, 0)))
    vals = {f: empty for f in ODE_FIELDS}
    structs = []
    while args and getattr(args[0], "is_struct", False):
        structs.append(args.pop(0))
    pairs = _name_value_pairs("odeset", ODE_FIELDS, args)
    overridden = {canon for canon, _v in pairs}
    for old in structs:
        _absorb_ode_struct(old, vals, overridden)
    for canon, v in pairs:
        vals[canon] = v
    return [StructValue.scalar([(f, vals[f]) for f in ODE_FIELDS] + [(f, v) for f, v in vals.items() if f not in ODE_FIELDS])]


def _setter(fname, fields):
    def fn(args, *, nargout=1):
        args = list(args)
        if fname != "odeset":
            return _legacy_setter(fname, fields, args)
        return _build_odeset(args)

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
    """First case-insensitive match. ODE solvers do not use this: a later alias would be hidden."""
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


# Applied options are read by the step loop. Any other nonempty ODE_FIELDS value
# is refused before f(t, y) is called. Only the five switches below treat 'off'
# as that same path. Every other unimplemented field must be empty. Public
# odeset/ode45 pages name the fields and do not publish an identifier for this
# gap, so the id is OpenMATLAB's.
_APPLIED_OPTIONS = frozenset({"AbsTol", "InitialStep", "MaxStep", "Refine", "RelTol"})
_OFF_DEFAULT_OPTIONS = frozenset({"BDF", "JConstant", "NormControl", "Stats", "Vectorized"})
_OPTION_CHECK_ORDER = ("Events", "Mass") + tuple(
    f for f in ODE_FIELDS if f not in _APPLIED_OPTIONS and f not in ("Events", "Mass")
)


def _is_function_handle(v) -> bool:
    kind = getattr(v, "matlab_class", None)
    return callable(kind) and kind() == "function_handle"


def _value_unset(v) -> bool:
    """True for the odeset placeholder ``[]`` and for blank text. A function handle is set."""
    if v is None:
        return True
    if _is_function_handle(v):
        return False
    numel = getattr(v, "numel", None)
    if callable(numel) and numel() == 0:
        return True
    try:
        text = _text(v)
    except ValueError:
        return False
    return text is not None and text == ""


def _is_off(v) -> bool:
    try:
        text = _text(v)
    except ValueError:
        return False
    return text is not None and text.lower() == "off"


def _scalar_option_struct(name, opts):
    """The one element that carries option values, or None when nothing is set.

    A struct array keeps every field name on the type even after ``o(:) = []``,
    but then it has no element to read. Indexing element 0 would raise. More
    than one element is not a scalar options structure: reading only the first
    would drop a value stored later.
    """
    if opts is None:
        return None
    if not getattr(opts, "is_struct", False):
        numel = getattr(opts, "numel", None)
        if callable(numel) and numel() == 0:
            return None
        raise _err(
            f"{name}: the options argument must be a structure created with odeset, or [].",
            f"OpenMATLAB:{name}:OptionsNotStructure",
        )
    n = opts.numel()
    if n == 0:
        return None
    if n != 1:
        raise _err(
            f"{name}: the options argument must be a scalar structure created with odeset, or [].",
            f"OpenMATLAB:{name}:OptionsNotStructure",
        )
    return opts


def _matching_fields(opts, opt):
    return [opts.get(f) for f in opts.fields if f.lower() == opt.lower()]


def _value_key(v):
    """Equality for two set spellings of one option. Text ignores case; numbers do not."""
    if _is_function_handle(v):
        return ("fh", id(v))
    try:
        text = _text(v)
    except ValueError:
        text = None
    if text is not None:
        return ("text", text.lower())
    buf = getattr(v, "backend_buffer", None)
    if callable(buf):
        a = np.asarray(buf(), dtype=float).reshape(-1)
        return ("num", tuple(float(x) for x in a))
    return ("obj", id(v))


def _distinct_set_value(who, opts, opt):
    """The one set value among case spellings, or None when every spelling is unset.

    ``opts`` is a scalar structure. Two set values that are not equal raise
    AmbiguousOption for ``who`` (the solver, or odeset when it is copying).
    """
    chosen = None
    key = None
    for v in _matching_fields(opts, opt):
        if _value_unset(v):
            continue
        got = _value_key(v)
        if chosen is None:
            chosen, key = v, got
            continue
        if key != got:
            raise _err(
                f"{who}: option '{opt}' is specified more than once with different values.",
                f"OpenMATLAB:{who}:AmbiguousOption",
            )
    return chosen


def _extract_applied(v):
    try:
        text = _text(v)
    except ValueError:
        text = None
    if text is not None:
        return ("text", text)
    a = _arr(v).reshape(-1)
    if a.size > 1:
        return ("vec", tuple(float(x) for x in a))
    return ("num", float(a[0]))


def _applied_option(name, opts, opt, default):
    """Every case spelling of an applied option. Disagreeing set values are an error."""
    if opts is None:
        return default
    chosen = _distinct_set_value(name, opts, opt)
    if chosen is None:
        return default
    kind, value = _extract_applied(chosen)
    if kind == "vec":
        return np.asarray(value, dtype=float)
    return value


def _reject_unimplemented_options(name, opts):
    """Refuse a requested option this solver does not apply, before any f(t, y) call.

    Every case spelling is inspected. An empty canonical field does not hide
    ``events`` or ``mass``. Only ``_OFF_DEFAULT_OPTIONS`` may be the text off.
    """
    if opts is None:
        return
    for opt in _OPTION_CHECK_ORDER:
        for v in _matching_fields(opts, opt):
            if _value_unset(v):
                continue
            if opt in _OFF_DEFAULT_OPTIONS and _is_off(v):
                continue
            raise _err(
                f"{name}: option '{opt}' is not supported.",
                f"OpenMATLAB:{name}:UnsupportedOption",
            )


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
        opts = _scalar_option_struct(name, args[3] if len(args) > 3 else None)
        _reject_unimplemented_options(name, opts)
        tspan = _arr(args[1]).reshape(-1)
        y0 = _arr(args[2]).reshape(-1)
        if tspan.size < 2:
            raise _err("The time vector TSPAN must have at least two elements.", f"MATLAB:{name}:TspanLength")
        if tspan[0] == tspan[-1]:
            raise _err("The last entry in tspan must be different from the first entry.", "MATLAB:odearguments:TspanEndpointsNotDistinct")
        rtol = float(_applied_option(name, opts, "RelTol", 1e-3))
        atol = np.asarray(_applied_option(name, opts, "AbsTol", 1e-6), dtype=float)
        if rtol < 100 * np.finfo(float).eps:
            rtol = 100 * np.finfo(float).eps
        refine = int(_applied_option(name, opts, "Refine", tab["refine"]))
        t0, tf = float(tspan[0]), float(tspan[-1])
        direction = np.sign(tf - t0)
        maxstep = float(_applied_option(name, opts, "MaxStep", 0.1 * abs(tf - t0)))
        # Every applied option is resolved here, before the first RHS call.
        h_user = float(_applied_option(name, opts, "InitialStep", 0.0))
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
        h = h_user
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


# -- quadrature (quad; the adaptive Gauss-Kronrod family lives in quadrature.py) ----------


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
