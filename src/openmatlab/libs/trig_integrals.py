"""Sine and cosine integrals sinint/cosint (C-E5 #765 T2 burn-down).

Clean-room, NumPy only.  Power series (DLMF 6.6.5, 6.6.6) for |z| <= 2; otherwise the
exponential-integral relations DLMF 6.5.5/6.5.6 on the right half-plane, oddness of Si and
DLMF 6.4.4 (Ci(z e^{+-pi i}) = Ci(z) +- pi i) on the left, and Chi/Shi on the imaginary axis.
"""

from __future__ import annotations

import cmath
import math
from typing import Callable, Dict

import numpy as np

from .burndown_builtins import _need, _num
from .incgamma_builtins import EPS, EULER, _finish, _single, expint1

HALF_PI = math.pi / 2


def _si_series(z: complex) -> complex:
    s, term, z2 = z, z, z * z
    for k in range(1, 200):
        term *= -z2 / ((2 * k) * (2 * k + 1))
        t = term / (2 * k + 1)
        s += t
        if abs(t) <= EPS * abs(s) * 0.25:
            break
    return s


def _ci_series(z: complex) -> complex:
    s, term, z2 = 0j, 1 + 0j, z * z
    for k in range(1, 200):
        term *= -z2 / ((2 * k - 1) * (2 * k))
        t = term / (2 * k)
        s += t
        if abs(t) <= EPS * max(abs(s), 1e-300) * 0.25:
            break
    return EULER + cmath.log(z) + s


def _chi_shi(y: float):
    """(Chi(y), Shi(y)) for real y > 2 via E1(y) and Ei(y) = -Re E1(-y)."""
    e1 = expint1(complex(y, 0)).real
    ei = -expint1(complex(-y, 0)).real
    return (ei - e1) / 2, (ei + e1) / 2


def _right(z: complex):
    """(Si, Ci) for Re z > 0 and |z| > 2."""
    a, b = expint1(1j * z), expint1(-1j * z)
    return HALF_PI + (a - b) / 2j, -(a + b) / 2


def sinint1(z: complex, real_in: bool) -> complex:
    if cmath.isnan(z):
        return complex(math.nan, 0)
    if math.isinf(z.real) and z.imag == 0:
        return complex(math.copysign(HALF_PI, z.real), 0)
    if abs(z) <= 2:
        return _si_series(z)
    if z.real == 0:
        _, shi = _chi_shi(abs(z.imag))
        return complex(0, math.copysign(shi, z.imag))
    if z.real < 0:
        return -sinint1(-z, real_in)
    return _right(z)[0]


def cosint1(z: complex, real_in: bool) -> complex:
    if cmath.isnan(z):
        return complex(math.nan, 0)
    # a real input (or a complex one with a +-0 imaginary part) on the negative axis picks +-pi i
    up = (not real_in and math.copysign(1, z.imag) > 0) or (real_in and True)
    if z == 0:
        if math.copysign(1, z.real) > 0:
            return complex(-math.inf, 0)
        return complex(-math.inf, math.pi if up else -math.pi)
    if math.isinf(z.real) and z.imag == 0:
        return 0j if z.real > 0 else complex(0, math.pi if up else -math.pi)
    if abs(z) <= 2:
        if z.real < 0 and z.imag == 0:
            return _ci_series(-z) + complex(0, math.pi if up else -math.pi)
        return _ci_series(z)
    if z.real == 0:
        chi, _ = _chi_shi(abs(z.imag))
        return complex(chi, math.copysign(HALF_PI, z.imag))
    if z.real < 0:
        sgn = 1 if (z.imag > 0 or (z.imag == 0 and up)) else -1
        return _right(-z)[1] + complex(0, sgn * math.pi)
    return _right(z)[1]


def _make(fn, name):
    def f(args, *, nargout=1):
        _need(args, 1, name)
        x = _num(args[0], name)
        real_in = not np.iscomplexobj(x)
        vals = np.array([fn(complex(v), real_in) for v in x.reshape(-1)], dtype=complex).reshape(x.shape)
        if real_in and (name == "sinint" or np.all(x.reshape(-1) >= 0) and not np.any(np.signbit(x))):
            vals = vals.real
        return _finish(vals, _single(args[0]))
    return f


def register(builtins: Dict[str, Callable]) -> None:
    builtins.setdefault("sinint", _make(sinint1, "sinint"))
    builtins.setdefault("cosint", _make(cosint1, "cosint"))
