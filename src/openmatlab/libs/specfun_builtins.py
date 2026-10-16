"""Special functions and small matrix/integer helpers in pure NumPy (#766, corpus missing-builtin).

gamma, gammaln, beta, psi, erf, erfc, erfinv, erfcinv, besselj, bessely, besseli, besselk,
besselh, airy, ellipj, perms, bitget, dec2base, toeplitz, peaks.

Clean-room implementations from public mathematical definitions (DLMF / Abramowitz-Stegun
integral representations, AGM descent); no MATLAB or Octave code was consulted.
Bessel functions of real order and real argument use Gauss-Legendre quadrature of the
standard integral representations (DLMF 10.9.6, 10.9.7, 10.32.4, 10.32.9); negative real
arguments use the reflection J_nu(-x) = exp(i*pi*nu) J_nu(x).
"""

from __future__ import annotations

import itertools
import math
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _num(v, fn):
    buf = getattr(v, "backend_buffer", None)
    if buf is None:
        raise _err(f"Undefined function '{fn}' for input arguments of type '{v.matlab_class()}'.",
                   "MATLAB:UndefinedFunction")
    a = np.asarray(buf())
    if a.dtype == np.bool_ or a.dtype.kind in "iu":
        a = a.astype(np.float64)
    return a


def _out(a, like=None):
    a = np.asarray(a)
    if np.iscomplexobj(a):
        a = a.astype(np.complex128) if np.any(a.imag) else np.ascontiguousarray(a.real, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    if like is not None and like.dtype == np.float32:
        a = a.astype(np.complex64 if np.iscomplexobj(a) else np.float32)
    return NDArrayValue(a)


def _bcast(a, b, fn):
    if a.size == 1 or b.size == 1 or a.shape == b.shape:
        return np.broadcast_arrays(a, b)
    raise _err(f"{fn}: inputs must be the same size or either can be a scalar.", "MATLAB:sizeDimensionsMustMatch")


def _elementwise(f, a):
    flat = a.reshape(-1)
    out = np.array([f(float(x)) for x in flat], dtype=np.float64)
    return out.reshape(a.shape)


# ---- gamma family -----------------------------------------------------------------------

def _gamma1(x):
    if math.isnan(x):
        return math.nan
    if x == math.floor(x) and x <= 0:
        return math.inf
    try:
        return math.gamma(x)
    except OverflowError:
        return math.inf


def _lgamma1(x):
    if math.isnan(x):
        return math.nan
    if x < 0:
        raise _err("Input must be nonnegative.", "MATLAB:gammaln:NegativeArg")
    if x == 0 or math.isinf(x):
        return math.inf
    return math.lgamma(x)


def _psi1(x):
    if math.isnan(x):
        return math.nan
    if x <= 0 and x == math.floor(x):
        return -math.inf
    acc = 0.0
    if x < 0:  # reflection
        return _psi1(1.0 - x) - math.pi / math.tan(math.pi * x)
    while x < 10.0:
        acc -= 1.0 / x
        x += 1.0
    x2 = 1.0 / (x * x)
    series = x2 * (1 / 12 - x2 * (1 / 120 - x2 * (1 / 252 - x2 * (1 / 240 - x2 * (1 / 132)))))
    return acc + math.log(x) - 0.5 / x - series


def _gamma(args, *, nargout=1):
    a = _num(args[0], "gamma")
    return (_out(_elementwise(_gamma1, a), a),)


def _gammaln(args, *, nargout=1):
    a = _num(args[0], "gammaln")
    return (_out(_elementwise(_lgamma1, a), a),)


def _beta(args, *, nargout=1):
    if len(args) != 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    a, b = _bcast(_num(args[0], "beta"), _num(args[1], "beta"), "beta")
    out = np.empty(a.shape)
    for ix in np.ndindex(*a.shape):
        x, y = float(a[ix]), float(b[ix])
        if x > 0 and y > 0:
            out[ix] = math.exp(math.lgamma(x) + math.lgamma(y) - math.lgamma(x + y))
        else:
            gx, gy, gxy = _gamma1(x), _gamma1(y), _gamma1(x + y)
            out[ix] = gx * gy / gxy if not math.isinf(gxy) else 0.0
    return (_out(out),)


def _psi(args, *, nargout=1):
    if len(args) == 2:
        raise _err("psi(k, x) for k > 0 is not supported yet.", "openmatlab:psi:polygamma")
    a = _num(args[0], "psi")
    return (_out(_elementwise(_psi1, a), a),)


# ---- error function family --------------------------------------------------------------

def _erf(args, *, nargout=1):
    a = _num(args[0], "erf")
    return (_out(_elementwise(math.erf, a), a),)


def _erfc(args, *, nargout=1):
    a = _num(args[0], "erfc")
    return (_out(_elementwise(math.erfc, a), a),)


def _erfinv1(y):
    if math.isnan(y) or y < -1 or y > 1:
        return math.nan
    if y == 1:
        return math.inf
    if y == -1:
        return -math.inf
    if y == 0:
        return 0.0
    # Giles' single-precision approximation as a start, then Newton steps on erf
    w = -math.log((1.0 - y) * (1.0 + y))
    if w < 5:
        w -= 2.5
        p = 2.81022636e-08
        for c in (3.43273939e-07, -3.5233877e-06, -4.39150654e-06, 0.00021858087, -0.00125372503,
                  -0.00417768164, 0.246640727, 1.50140941):
            p = c + p * w
    else:
        w = math.sqrt(w) - 3
        p = -0.000200214257
        for c in (0.000100950558, 0.00134934322, -0.00367342844, 0.00573950773, -0.0076224613,
                  0.00943887047, 1.00167406, 2.83297682):
            p = c + p * w
    x = p * y
    for _ in range(4):
        err = math.erf(x) - y
        x -= err / (2.0 / math.sqrt(math.pi) * math.exp(-x * x))
    return x


def _erfcinv1(y):
    if math.isnan(y) or y < 0 or y > 2:
        return math.nan
    if y == 0:
        return math.inf
    if y == 2:
        return -math.inf
    if y > 1e-3:
        x = _erfinv1(1.0 - y)
    else:  # tail: Newton on erfc for relative accuracy
        x = math.sqrt(-math.log(y * math.sqrt(math.pi)))
    for _ in range(6):
        d = -2.0 / math.sqrt(math.pi) * math.exp(-x * x)
        if d == 0:
            break
        x -= (math.erfc(x) - y) / d
    return x


def _erfinv(args, *, nargout=1):
    a = _num(args[0], "erfinv")
    return (_out(_elementwise(_erfinv1, a), a),)


def _erfcinv(args, *, nargout=1):
    a = _num(args[0], "erfcinv")
    return (_out(_elementwise(_erfcinv1, a), a),)


# ---- Bessel functions -------------------------------------------------------------------

_GL_CACHE: Dict[int, tuple] = {}


def _gl(n):
    r = _GL_CACHE.get(n)
    if r is None:
        r = np.polynomial.legendre.leggauss(n)
        _GL_CACHE[n] = r
    return r


def _quad(f, a, b, n):
    x, w = _gl(n)
    t = 0.5 * (b - a) * x + 0.5 * (b + a)
    return 0.5 * (b - a) * float(np.dot(w, f(t)))


def _npts(x):
    return int(min(4000, 60 + 2.0 * abs(x)))


def _tail_end(x):
    # e^{-x sinh t} < 1e-300 beyond asinh(700/x)
    return math.asinh(700.0 / x) if x > 0 else 50.0


def _jy_pos(nu, x):
    """J_nu(x), Y_nu(x) for real nu and x > 0 (DLMF 10.9.6, 10.9.7)."""
    n = _npts(x)
    # split [0, pi] for oscillatory integrands
    pieces = max(1, int(abs(x) // 50) + 1)
    J1 = Y1 = 0.0
    for k in range(pieces):
        lo, hi = math.pi * k / pieces, math.pi * (k + 1) / pieces
        J1 += _quad(lambda t: np.cos(nu * t - x * np.sin(t)), lo, hi, n // pieces + 40)
        Y1 += _quad(lambda t: np.sin(x * np.sin(t) - nu * t), lo, hi, n // pieces + 40)
    J1 /= math.pi
    Y1 /= math.pi
    T = _tail_end(x) + abs(nu)
    snu = math.sin(nu * math.pi)
    cnu = math.cos(nu * math.pi)
    segs = np.linspace(0.0, T, 9)
    J2 = Y2 = 0.0
    for lo, hi in zip(segs[:-1], segs[1:]):
        if snu != 0.0 and not (nu == math.floor(nu)):
            J2 += _quad(lambda t: np.exp(-x * np.sinh(t) - nu * t), lo, hi, 80)
        Y2 += _quad(lambda t: (np.exp(nu * t - x * np.sinh(t)) + cnu * np.exp(-nu * t - x * np.sinh(t))), lo, hi, 80)
    J = J1 - (snu / math.pi) * J2 if nu != math.floor(nu) else J1
    Y = Y1 - Y2 / math.pi
    return J, Y


def _ik_pos(nu, x):
    """I_nu(x), K_nu(x) for real nu and x > 0 (DLMF 10.32.4, 10.32.9), scaled by exp(-x) internally."""
    n = int(min(1000, 80 + 4.0 * math.sqrt(abs(x))))
    I1 = _quad(lambda t: np.exp(-2.0 * x * np.sin(0.5 * t) ** 2) * np.cos(nu * t), 0.0, math.pi, n) / math.pi
    T = math.acosh(1.0 + 700.0 / x) + abs(nu) if x > 0 else 50.0
    segs = np.linspace(0.0, T, 9)
    I2 = K = 0.0
    for lo, hi in zip(segs[:-1], segs[1:]):
        if nu != math.floor(nu):
            I2 += _quad(lambda t: np.exp(-x * (np.cosh(t) + 1.0) - nu * t), lo, hi, 80)
        K += _quad(lambda t: np.exp(-2.0 * x * np.sinh(0.5 * t) ** 2) * np.cosh(nu * t), lo, hi, 80)
    I_scaled = I1 - (math.sin(nu * math.pi) / math.pi) * I2 if nu != math.floor(nu) else I1
    return I_scaled, K  # I*exp(-x), K*exp(x)


def _series(kind, nu, x):
    """Ascending series (DLMF 10.2.2, 10.25.2) for small arguments."""
    h = 0.5 * x
    sgn = -1.0 if kind == "j" else 1.0
    try:
        lt = nu * math.log(h) - math.lgamma(nu + 1.0) if nu + 1.0 > 0 else None
    except ValueError:
        lt = None
    if lt is not None:
        term = math.exp(lt)
    else:
        g = _gamma1(nu + 1.0)
        term = (h ** nu) / g if not math.isinf(g) else 0.0
    total = term
    q = sgn * h * h
    for k in range(1, 500):
        denom = k * (k + nu)
        term *= q / denom
        total += term
        if abs(term) <= 1e-17 * abs(total) and k > abs(nu):
            break
    return total


def _bessel_point(kind, nu, z, scaled=False):
    if isinstance(z, complex) and z.imag != 0:
        raise _err(f"bessel{kind}: complex arguments are not supported yet.", "openmatlab:bessel:complex")
    x = float(z.real if isinstance(z, complex) else z)
    if math.isnan(x) or math.isnan(nu):
        return math.nan
    isint = nu == math.floor(nu)
    if x == 0:
        if kind == "j":
            return 1.0 if nu == 0 else (0.0 if nu > 0 or isint else math.inf)
        if kind == "i":
            return 1.0 if nu == 0 else (0.0 if nu > 0 or isint else math.inf)
        return -math.inf if kind == "y" else math.inf
    if math.isinf(x):
        return {"j": 0.0, "y": 0.0, "i": math.inf, "k": 0.0}[kind]
    if x < 0:
        refl = complex(math.cos(math.pi * nu), math.sin(math.pi * nu))
        if kind == "j":
            v = refl * _bessel_point("j", nu, -x)
        elif kind == "i":
            v = refl * _bessel_point("i", nu, -x)
        elif kind == "y":  # DLMF 10.11.1 (principal branch, arg = +pi)
            j, y = _jy_pos(nu, -x)
            v = complex(math.cos(math.pi * nu), -math.sin(math.pi * nu)) * y + 2j * math.cos(math.pi * nu) * j
        else:  # DLMF 10.34.2
            i_s, k_s = _ik_pos(nu, -x)
            v = complex(math.cos(math.pi * nu), -math.sin(math.pi * nu)) * k_s * math.exp(x) - 1j * math.pi * i_s * math.exp(-x)
        if isint:
            v = complex(round(v.real, 300), v.imag)
            if kind in ("j", "i"):
                v = v.real
        return v
    if kind in ("j", "i") and (x < 4.0 or x * x < 4.0 * (abs(nu) + 1.0)) and not (isint and nu < 0):
        v = _series(kind, nu, x)
        return v * math.exp(-x) if (scaled and kind == "i") else v
    if kind in ("j", "i") and isint and nu < 0:
        return (-1.0) ** int(-nu) * _bessel_point(kind, -nu, x, scaled) if kind == "j" else _bessel_point(kind, -nu, x, scaled)
    if kind in ("j", "y"):
        j, y = _jy_pos(nu, x)
        return j if kind == "j" else y
    i_s, k_s = _ik_pos(nu, x)
    if kind == "i":
        return i_s if scaled else i_s * math.exp(x)
    return k_s if scaled else k_s * math.exp(-x)


def _bessel(kind):
    fn = "bessel" + kind

    def impl(args, *, nargout=1):
        if len(args) < 2:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        nu, z = _bcast(_num(args[0], fn), _num(args[1], fn), fn)
        scaled = len(args) > 2 and bool(np.asarray(_num(args[2], fn)).reshape(-1)[0])
        out = np.empty(nu.shape, dtype=np.complex128)
        for ix in np.ndindex(*nu.shape):
            zz = z[ix]
            zz = complex(zz) if np.iscomplexobj(z) else float(zz)
            v = _bessel_point(kind, float(np.real(nu[ix])), zz, scaled and kind in ("i", "k"))
            if scaled and kind in ("j", "y") and isinstance(zz, complex):
                v *= math.exp(-abs(zz.imag))
            out[ix] = v
        return (_out(out),)

    return impl


def _besselh(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if len(args) == 2:
        nu, k, z = args[0], 1, args[1]
    else:
        nu, k, z = args[0], int(float(_num(args[1], "besselh").reshape(-1)[0])), args[2]
    if k not in (1, 2):
        raise _err("besselh: kind must be 1 or 2.", "MATLAB:besselh:BadKind")
    j = np.asarray(_bessel("j")([nu, z])[0].backend_buffer(), dtype=np.complex128)
    y = np.asarray(_bessel("y")([nu, z])[0].backend_buffer(), dtype=np.complex128)
    return (_out(j + 1j * y if k == 1 else j - 1j * y),)


_AI0 = 1.0 / (3.0 ** (2.0 / 3.0) * math.gamma(2.0 / 3.0))
_AIP0 = -1.0 / (3.0 ** (1.0 / 3.0) * math.gamma(1.0 / 3.0))
_BI0 = 1.0 / (3.0 ** (1.0 / 6.0) * math.gamma(2.0 / 3.0))
_BIP0 = 3.0 ** (1.0 / 6.0) / math.gamma(1.0 / 3.0)


def _airy1(k, x):
    """Airy functions of a real argument via Bessel functions of order 1/3 and 2/3 (DLMF 9.6)."""
    if math.isnan(x):
        return math.nan
    if x == 0:
        return (_AI0, _AIP0, _BI0, _BIP0)[k]
    r3 = math.sqrt(3.0)
    if x > 0:
        z = 2.0 / 3.0 * x ** 1.5
        if k == 0:
            return math.sqrt(x / 3.0) / math.pi * _bessel_point("k", 1.0 / 3.0, z)
        if k == 1:
            return -x / (math.pi * r3) * _bessel_point("k", 2.0 / 3.0, z)
        if k == 2:
            return math.sqrt(x / 3.0) * (_bessel_point("i", -1.0 / 3.0, z) + _bessel_point("i", 1.0 / 3.0, z))
        return x / r3 * (_bessel_point("i", -2.0 / 3.0, z) + _bessel_point("i", 2.0 / 3.0, z))
    t = -x
    z = 2.0 / 3.0 * t ** 1.5
    if k == 0:
        return math.sqrt(t) / 3.0 * (_bessel_point("j", 1.0 / 3.0, z) + _bessel_point("j", -1.0 / 3.0, z))
    if k == 1:
        return t / 3.0 * (_bessel_point("j", 2.0 / 3.0, z) - _bessel_point("j", -2.0 / 3.0, z))
    if k == 2:
        return math.sqrt(t / 3.0) * (_bessel_point("j", -1.0 / 3.0, z) - _bessel_point("j", 1.0 / 3.0, z))
    return t / r3 * (_bessel_point("j", -2.0 / 3.0, z) + _bessel_point("j", 2.0 / 3.0, z))


def _airy(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if len(args) == 1:
        k, zv = 0, args[0]
    else:
        k, zv = int(float(_num(args[0], "airy").reshape(-1)[0])), args[1]
    if k not in (0, 1, 2, 3):
        raise _err("airy: K must be 0, 1, 2 or 3.", "MATLAB:airy:BadK")
    z = _num(zv, "airy")
    if np.iscomplexobj(z) and np.any(np.imag(z)):
        raise _err("airy: complex arguments are not supported yet.", "openmatlab:airy:complex")
    z = np.real(z)
    return (_out(_elementwise(lambda x: _airy1(k, x), z)),)


# ---- Jacobi elliptic functions ----------------------------------------------------------

def _ellipj1(u, m, tol):
    if m < 0 or m > 1:
        raise _err("ellipj: M must be in the range 0 <= M <= 1.", "MATLAB:ellipj:MOutOfRange")
    if m < tol:
        return math.sin(u), math.cos(u), 1.0
    if m >= 1 - tol:
        s = 1.0 / math.cosh(u)
        return math.tanh(u), s, s
    a = [1.0]
    c = [math.sqrt(m)]
    b = math.sqrt(1.0 - m)
    n = 0
    while abs(c[n]) > tol and n < 60:
        a.append(0.5 * (a[n] + b))
        c.append(0.5 * (a[n] - b))
        b = math.sqrt(a[n] * b)
        n += 1
    phi = (2.0 ** n) * a[n] * u
    for i in range(n, 0, -1):
        phi = 0.5 * (phi + math.asin(c[i] / a[i] * math.sin(phi)))
    sn, cn = math.sin(phi), math.cos(phi)
    return sn, cn, math.sqrt(1.0 - m * sn * sn)


def _ellipj(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    u, m = _bcast(_num(args[0], "ellipj"), _num(args[1], "ellipj"), "ellipj")
    tol = float(_num(args[2], "ellipj").reshape(-1)[0]) if len(args) > 2 else np.finfo(float).eps
    sn, cn, dn = (np.empty(u.shape) for _ in range(3))
    for ix in np.ndindex(*u.shape):
        sn[ix], cn[ix], dn[ix] = _ellipj1(float(u[ix]), float(m[ix]), tol)
    return tuple(_out(v) for v in (sn, cn, dn))[: max(1, nargout)]


# ---- integer / matrix helpers -----------------------------------------------------------

def _perms(args, *, nargout=1):
    v = args[0]
    buf = np.asarray(v.backend_buffer()) if hasattr(v, "backend_buffer") else None
    if buf is None:
        raise _err("perms: input must be numeric, logical or char.", "MATLAB:perms:invalidInput")
    flat = buf.reshape(-1, order="F")
    n = flat.size
    if n == 0:
        return (NDArrayValue(np.empty((1, 0), dtype=buf.dtype)),)
    if n > 11:
        raise _err("perms: maximum array size exceeded.", "MATLAB:pmaxsize")
    order = list(itertools.permutations(range(n - 1, -1, -1)))
    out = flat[np.array(order, dtype=np.int64)]
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue):
        return (CharValue(rows=["".join(r) for r in out]),)
    return (NDArrayValue(out),)


def _bitget(args, *, nargout=1):
    if len(args) != 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    a_raw = np.asarray(args[0].backend_buffer())
    a, b = _bcast(_num(args[0], "bitget"), _num(args[1], "bitget"), "bitget")
    if np.any(a < 0) or np.any(a != np.floor(a)):
        raise _err("Double inputs must have integer values in the range of ASSUMEDTYPE.", "MATLAB:bitget:inputs")
    if np.any(b < 1) or np.any(b != np.floor(b)) or np.any(b > 53):
        raise _err("BIT must be between 1 and 53.", "MATLAB:bitget:BitOutOfRange")
    r = (a.astype(np.uint64) >> (b.astype(np.uint64) - np.uint64(1))) & np.uint64(1)
    dt = a_raw.dtype if a_raw.dtype.kind in "iu" else np.float64
    return (NDArrayValue(r.astype(dt)),)


def _dec2base(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue

    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    d = _num(args[0], "dec2base").reshape(-1, order="F")
    bv = args[1]
    if isinstance(bv, CharValue):
        symbols = bv.text
        base = len(symbols)
    else:
        base = int(float(_num(bv, "dec2base").reshape(-1)[0]))
        symbols = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:max(base, 0)]
    if base < 2 or base > 36 and not isinstance(bv, CharValue):
        raise _err("Base must be an integer between 2 and 36.", "MATLAB:dec2base:BaseOutOfRange")
    if np.any(d < 0) or np.any(d != np.floor(d)):
        raise _err("D must be a nonnegative integer.", "MATLAB:dec2base:FirstArg")
    width = int(float(_num(args[2], "dec2base").reshape(-1)[0])) if len(args) > 2 else 0
    rows = []
    for x in d:
        x = int(x)
        s = ""
        while True:
            s = symbols[x % base] + s
            x //= base
            if x == 0:
                break
        rows.append(s)
    w = max([width] + [len(s) for s in rows])
    return (CharValue(rows=[s.rjust(w, symbols[0]) for s in rows]),)


def _toeplitz(args, *, nargout=1):
    if not args or len(args) > 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if len(args) == 1:
        r = _num(args[0], "toeplitz").reshape(-1, order="F")
        if np.iscomplexobj(r):
            r = r.copy()
            r[0] = np.conj(r[0])
        c = np.conj(r)
    else:
        c = _num(args[0], "toeplitz").reshape(-1, order="F")
        r = _num(args[1], "toeplitz").reshape(-1, order="F")
    m, n = c.size, r.size
    dt = np.result_type(c, r, np.float64)
    out = np.empty((m, n), dtype=dt)
    for i in range(m):
        for j in range(n):
            out[i, j] = c[i - j] if i >= j else r[j - i]
    return (_out(out),)


def _peaks(args, *, nargout=1):
    if len(args) == 2:
        x, y = _num(args[0], "peaks"), _num(args[1], "peaks")
        if x.ndim == 2 and 1 in x.shape and y.ndim == 2 and 1 in y.shape and x.shape != y.shape:
            x, y = np.meshgrid(x.reshape(-1), y.reshape(-1))
    else:
        n = _num(args[0], "peaks") if args else np.array([49.0])
        v = np.linspace(-3, 3, int(n.reshape(-1)[0])) if n.size == 1 else n.reshape(-1)
        x, y = np.meshgrid(v, v)
    z = (3 * (1 - x) ** 2 * np.exp(-(x ** 2) - (y + 1) ** 2)
         - 10 * (x / 5 - x ** 3 - y ** 5) * np.exp(-x ** 2 - y ** 2)
         - 1 / 3 * np.exp(-(x + 1) ** 2 - y ** 2))
    if nargout >= 3:
        return (_out(x), _out(y), _out(z))
    return (_out(z),)


def register(builtins: Dict[str, Callable]) -> None:
    table = {
        "gamma": _gamma, "gammaln": _gammaln, "beta": _beta, "psi": _psi,
        "erf": _erf, "erfc": _erfc, "erfinv": _erfinv, "erfcinv": _erfcinv,
        "besselj": _bessel("j"), "bessely": _bessel("y"), "besseli": _bessel("i"), "besselk": _bessel("k"),
        "besselh": _besselh, "airy": _airy, "ellipj": _ellipj,
        "perms": _perms, "bitget": _bitget, "dec2base": _dec2base, "toeplitz": _toeplitz, "peaks": _peaks,
    }
    for k, v in table.items():
        builtins.setdefault(k, v)
