"""Incomplete gamma/beta functions, their inverses, expint and betaln in pure NumPy (C-E5 #765 T2 burn-down).

gammainc gammaincinv betainc betaincinv expint betaln.

Clean-room implementations from public definitions (DLMF 8.2, 8.7, 8.9, 8.17, 6.6, 6.12): power series
and modified Lentz continued fractions; inverses by safeguarded Newton iteration. No MATLAB or Octave
source was consulted.
"""

from __future__ import annotations

import cmath
import math
from typing import Callable, Dict

import numpy as np

from .burndown_builtins import _err, _is_text, _need, _num, _out

EPS = 2.220446049250313e-16
TINY = 1e-300
MAXIT = 200000
TAILS = ("lower", "upper")


def _tail(args, i, fn, allowed):
    if len(args) <= i:
        return allowed[0]
    if not _is_text(args[i]):
        raise _err(f"{fn}: TAIL must be a character vector.", f"MATLAB:{fn}:InvalidTail")
    t = args[i].text.lower()
    if t not in allowed:
        raise _err(f"{fn}: invalid value for TAIL: '{args[i].text}'.", f"MATLAB:{fn}:InvalidTail")
    return t


def _real(v, fn):
    a = _num(v, fn)
    if np.iscomplexobj(a):
        raise _err(f"{fn}: all inputs must be real.", f"MATLAB:{fn}:ComplexInput")
    return a


def _broadcast(arrs, fn):
    shapes = [a.shape for a in arrs if a.size != 1]
    if any(s != shapes[0] for s in shapes):
        raise _err(f"{fn}: inputs must be the same size or scalars.", "MATLAB:sizeDimensionsMustMatch")
    return np.broadcast_arrays(*arrs) if arrs else arrs


def _single(*vals):
    return any(np.asarray(v.backend_buffer()).dtype == np.float32 for v in vals if hasattr(v, "backend_buffer"))


def _finish(out, single):
    out = np.asarray(out)
    if single:
        out = out.astype(np.complex64 if np.iscomplexobj(out) else np.float32)
    return (_out(out),)


# ---- regularised incomplete gamma (DLMF 8.7.1 series, 8.9.2 continued fraction) ----------

def _gser(a, x):
    """sum_{n>=0} x^n / ((a+1)...(a+n)) = gammainc(x, a, 'scaledlower')."""
    term = total = 1.0
    ap = a
    for _ in range(MAXIT):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) <= abs(total) * EPS:
            break
    return total


def _gcf(a, x):
    """Continued fraction h with Q(a, x) = exp(-x) x^a / Gamma(a) * h (modified Lentz)."""
    b = x + 1.0 - a
    c = 1.0 / TINY
    d = 1.0 / b if b != 0 else 1.0 / TINY
    h = d
    for i in range(1, MAXIT):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = TINY if abs(d) < TINY else d
        c = b + an / c
        c = TINY if abs(c) < TINY else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) <= EPS:
            break
    return h


def _logpref(a, x):
    """log(x^a exp(-x) / Gamma(a + 1))."""
    return a * math.log(x) - x - math.lgamma(a + 1.0)


def gammainc1(x, a, tail="lower"):
    if math.isnan(x) or math.isnan(a):
        return math.nan
    if a < 0:
        raise _err("gammainc: A must be nonnegative.", "MATLAB:gammainc:NegativeArg")
    scaled = tail.startswith("scaled")
    upper = tail.endswith("upper")
    if x == 0:
        if scaled:
            return 1.0 if not upper else (math.inf if a > 0 else math.inf)
        return 1.0 if upper and a > 0 else (0.0 if a > 0 else (0.0 if upper else 1.0))
    if a == 0:
        if scaled:
            return math.exp(x) if not upper else 0.0
        return 0.0 if upper else 1.0
    if math.isinf(x):
        if x > 0:
            return (0.0 if upper else 1.0) if not scaled else (0.0 if upper else math.inf)
        return math.nan
    if x < 0:
        lower_s = _gser(a, x)
        if scaled:
            return lower_s if not upper else _scaled_from(a, x, 1.0 - _lower_unscaled_neg(a, x, lower_s))
        p = _lower_unscaled_neg(a, x, lower_s)
        return 1.0 - p if upper else p
    if x < a + 1.0:
        s = _gser(a, x)
        if scaled:
            if not upper:
                return s
            lp = _logpref(a, x)
            p = math.exp(lp) * s
            return (1.0 - p) * math.exp(-lp)
        p = math.exp(_logpref(a, x)) * s
        return 1.0 - p if upper else p
    h = _gcf(a, x)
    if scaled:
        if upper:
            return a * h
        lp = _logpref(a, x)
        q = math.exp(lp) * a * h
        return (1.0 - q) * math.exp(-lp)
    q = math.exp(_logpref(a, x)) * a * h
    return q if upper else 1.0 - q


def _lower_unscaled_neg(a, x, s):
    pref = cmath.exp(a * cmath.log(complex(x)) - x - math.lgamma(a + 1.0))
    v = pref * s
    return v.real if abs(v.imag) <= EPS * max(1.0, abs(v)) else v


def _scaled_from(a, x, q):
    return q * cmath.exp(-(a * cmath.log(complex(x)) - x - math.lgamma(a + 1.0)))


def _gammainc(args, *, nargout=1):
    _need(args, 2, "gammainc")
    tail = _tail(args, 2, "gammainc", ("lower", "upper", "scaledlower", "scaledupper"))
    x, a = _broadcast([_real(args[0], "gammainc"), _real(args[1], "gammainc")], "gammainc")
    if np.any(a < 0):
        raise _err("gammainc: A must be nonnegative.", "MATLAB:gammainc:NegativeArg")
    vals = [gammainc1(float(xi), float(ai), tail) for xi, ai in zip(x.reshape(-1), a.reshape(-1))]
    cplx = any(isinstance(v, complex) for v in vals)
    out = np.array(vals, dtype=complex if cplx else float).reshape(x.shape)
    return _finish(out, _single(*args[:2]))


def gammaincinv1(y, a, tail="lower"):
    if math.isnan(y) or math.isnan(a) or y < 0 or y > 1:
        return math.nan
    p = y if tail == "lower" else 1.0 - y
    if p == 0:
        return 0.0
    if p == 1 or a == 0:
        return math.inf if a > 0 else (0.0 if p < 1 else math.inf)
    q = 1.0 - p if tail == "lower" else y
    # initial guess (Wilson-Hilferty for a >= 1, small-x power law otherwise)
    if a >= 1:
        t = math.sqrt(-2 * math.log(min(p, q)))
        z = t - (2.30753 + 0.27061 * t) / (1 + t * (0.99229 + 0.04481 * t))
        z = -z if p < 0.5 else z
        x = max(1e-3, a * (1 - 1 / (9 * a) + z / (3 * math.sqrt(a))) ** 3)
    else:
        lp = math.log(max(p, TINY)) + math.lgamma(a + 1.0)
        x = math.exp(lp / a) if p < 0.9 else 1.0 - math.log(max(q, TINY))
    lo, hi = 0.0, math.inf
    for _ in range(200):
        if tail == "lower":
            f = gammainc1(x, a) - p
        else:
            f = q - gammainc1(x, a, "upper")
        if f > 0:
            hi = min(hi, x)
        else:
            lo = max(lo, x)
        dens = math.exp((a - 1) * math.log(x) - x - math.lgamma(a)) if x > 0 else math.inf
        nx = x - f / dens if dens > 0 and math.isfinite(dens) else math.nan
        if not math.isfinite(nx) or nx <= lo or nx >= hi:
            nx = (lo + hi) / 2 if math.isfinite(hi) else max(2 * x, x + 1)
        if abs(nx - x) <= 4 * EPS * abs(nx):
            return nx
        x = nx
    return x


def _gammaincinv(args, *, nargout=1):
    _need(args, 2, "gammaincinv")
    tail = _tail(args, 2, "gammaincinv", TAILS)
    y, a = _broadcast([_real(args[0], "gammaincinv"), _real(args[1], "gammaincinv")], "gammaincinv")
    if np.any(a < 0):
        raise _err("gammaincinv: A must be nonnegative.", "MATLAB:gammaincinv:NegativeArg")
    out = np.array([gammaincinv1(float(yi), float(ai), tail) for yi, ai in zip(y.reshape(-1), a.reshape(-1))])
    return _finish(out.reshape(y.shape), _single(*args[:2]))


# ---- regularised incomplete beta (DLMF 8.17.22 continued fraction) ------------------------

def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = TINY if abs(d) < TINY else d
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = TINY if abs(d) < TINY else d
        c = 1.0 + aa / c
        c = TINY if abs(c) < TINY else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = TINY if abs(d) < TINY else d
        c = 1.0 + aa / c
        c = TINY if abs(c) < TINY else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) <= EPS:
            break
    return h


def _lbeta(a, b):
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def betainc1(x, a, b, upper=False):
    if math.isnan(x) or math.isnan(a) or math.isnan(b):
        return math.nan
    if x <= 0:
        return 1.0 if upper else 0.0
    if x >= 1:
        return 0.0 if upper else 1.0
    if a == 0 or b == 0:
        if a == 0 and b == 0:
            return math.nan
        lower = 1.0 if a == 0 else 0.0
        return 1.0 - lower if upper else lower
    if math.isinf(a) or math.isinf(b):
        if math.isinf(a) and math.isinf(b):
            return math.nan
        lower = 0.0 if math.isinf(a) else 1.0
        return 1.0 - lower if upper else lower
    if x < (a + 1.0) / (a + b + 2.0):
        lf = a * math.log(x) + b * math.log1p(-x) - _lbeta(a, b)
        v = math.exp(lf) * _betacf(a, b, x) / a
        return 1.0 - v if upper else v
    lf = a * math.log(x) + b * math.log1p(-x) - _lbeta(a, b)
    v = math.exp(lf) * _betacf(b, a, 1.0 - x) / b
    return v if upper else 1.0 - v


def _betainc(args, *, nargout=1):
    _need(args, 3, "betainc")
    tail = _tail(args, 3, "betainc", TAILS)
    x, a, b = _broadcast([_real(args[i], "betainc") for i in range(3)], "betainc")
    if np.any((x < 0) | (x > 1)):
        raise _err("betainc: X must be in the interval [0, 1].", "MATLAB:betainc:XoutOfRange")
    if np.any(a < 0) or np.any(b < 0):
        raise _err("betainc: A and B must be nonnegative.", "MATLAB:betainc:NegativeArg")
    out = np.array([betainc1(float(xi), float(ai), float(bi), tail == "upper")
                    for xi, ai, bi in zip(x.reshape(-1), a.reshape(-1), b.reshape(-1))])
    return _finish(out.reshape(x.shape), _single(*args[:3]))


def betaincinv1(y, a, b, upper=False):
    if math.isnan(y) or math.isnan(a) or math.isnan(b) or y < 0 or y > 1:
        return math.nan
    p = 1.0 - y if upper else y
    if (y == 0 and not upper) or (y == 1 and upper):
        return 0.0
    if (y == 1 and not upper) or (y == 0 and upper):
        return 1.0
    lo, hi = 0.0, 1.0
    mean = a / (a + b)
    x = min(max(mean, 1e-8), 1 - 1e-8)
    lb = _lbeta(a, b)
    for _ in range(300):
        f = (betainc1(x, a, b) - p) if not upper else (y - betainc1(x, a, b, True))
        if f > 0:
            hi = x
        else:
            lo = x
        if f == 0:
            return x
        dens = math.exp((a - 1) * math.log(x) + (b - 1) * math.log1p(-x) - lb)
        nx = x - f / dens if dens > 0 and math.isfinite(dens) else math.nan
        if not (lo < nx < hi):
            nx = (lo + hi) / 2
        if abs(nx - x) <= 4 * EPS * max(abs(nx), TINY) or hi - lo <= 4 * EPS * max(abs(nx), TINY):
            return nx
        x = nx
    return x


def _betaincinv(args, *, nargout=1):
    _need(args, 3, "betaincinv")
    tail = _tail(args, 3, "betaincinv", TAILS)
    y, a, b = _broadcast([_real(args[i], "betaincinv") for i in range(3)], "betaincinv")
    out = np.array([betaincinv1(float(yi), float(ai), float(bi), tail == "upper")
                    for yi, ai, bi in zip(y.reshape(-1), a.reshape(-1), b.reshape(-1))])
    return _finish(out.reshape(y.shape), _single(*args[:3]))


def _betaln(args, *, nargout=1):
    _need(args, 2, "betaln")
    a, b = _broadcast([_real(args[0], "betaln"), _real(args[1], "betaln")], "betaln")
    out = np.array([_lbeta(float(x), float(y)) if x > 0 and y > 0 else
                    (math.inf if (x == 0 or y == 0) else math.nan)
                    for x, y in zip(a.reshape(-1), b.reshape(-1))])
    return _finish(out.reshape(a.shape), _single(*args[:2]))


# ---- exponential integral E1 (DLMF 6.6.2 series, 6.9 continued fraction, 6.12.1 asymptotic) ----

EULER = 0.5772156649015329


def expint1(z: complex) -> complex:
    if z == 0:
        return complex(math.inf, 0)
    if cmath.isnan(z):
        return complex(math.nan, 0)
    if z.real == math.inf:
        return 0j
    if z.real == -math.inf:
        return complex(-math.inf, -math.pi)
    az = abs(z)
    if az <= 2.0 or (z.real < 0 and az < 40 and abs(z.imag) < 1e-300 + 0.5 * az):
        if az > 2.0 and z.real < 0 and abs(z.imag) == 0:  # -Ei(|x|) - i*pi via Ei series (no cancellation)
            t = -z.real
            s, term = 0.0, 1.0
            for k in range(1, 500):
                term *= t / k
                s += term / k
                if term / k < EPS * abs(s):
                    break
            return complex(-(EULER + math.log(t) + s), -math.pi)
        s, term = 0j, 1 + 0j
        for k in range(1, 500):
            term *= -z / k
            s += term / k
            if abs(term / k) < EPS * abs(s):
                break
        return -EULER - cmath.log(z) - s
    if az >= 40:
        s, term = 1 + 0j, 1 + 0j
        for k in range(1, 60):
            nt = term * (-k / z)
            if abs(nt) > abs(term):
                break
            term = nt
            s += term
            if abs(term) < EPS * abs(s):
                break
        r = cmath.exp(-z) / z * s
        if z.real < 0 and z.imag == 0:
            r = complex(r.real, -math.pi)
        return r
    # modified Lentz continued fraction E1(z) = exp(-z) / (z + 1 - 1/(z + 3 - 4/(z + 5 - ...)))
    b = z + 1
    c = 1 / TINY
    d = 1 / b
    h = d
    for i in range(1, MAXIT):
        an = -i * i
        b += 2
        d = 1 / (an * d + b)
        c = b + an / c
        delta = c * d
        h *= delta
        if abs(delta - 1) <= EPS:
            break
    r = h * cmath.exp(-z)
    if z.real < 0 and z.imag == 0:
        r = complex(r.real, -math.pi)
    return r


def _expint(args, *, nargout=1):
    _need(args, 1, "expint")
    x = _num(args[0], "expint")
    vals = np.array([expint1(complex(v)) for v in x.reshape(-1)], dtype=complex).reshape(x.shape)
    if not np.iscomplexobj(x) and np.all(x.reshape(-1) >= 0):
        vals = vals.real
    return _finish(vals, _single(args[0]))


def register(builtins: Dict[str, Callable]) -> None:
    table = {"gammainc": _gammainc, "gammaincinv": _gammaincinv, "betainc": _betainc,
             "betaincinv": _betaincinv, "betaln": _betaln, "expint": _expint}
    for k, v in table.items():
        builtins.setdefault(k, v)
