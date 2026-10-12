"""idivide / bitand / bitor / bitxor / bitshift (#462)."""

from __future__ import annotations

from fractions import Fraction
import math
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics import intclass as ic
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.value import Array, Value

_FLINT = 2 ** 53


def _err(msg: str):
    from openmatlab.libs.numeric_builtins import BuiltinError

    return BuiltinError(msg)


def _buf(name: str, v: Value) -> np.ndarray:
    if not isinstance(v, Array):
        raise _err(f"{name}: inputs must be numeric")
    b = np.asarray(v.backend_buffer())
    if np.iscomplexobj(b):
        raise _err(f"{name}: inputs must be real")
    return b.reshape(1, 1) if b.ndim == 0 else b


def _pair(name: str, a: np.ndarray, b: np.ndarray):
    try:
        dt = ic.result_dtype(a, b)
    except ic.IntClassError as exc:
        raise _err(f"{name}: {exc}") from None
    if a.size != 1 and b.size != 1 and a.shape != b.shape:
        raise _err(f"{name}: Matrix dimensions must agree.")
    x, y = np.broadcast_arrays(a, b)
    return dt, x, y


def _idivide(args, *, nargout=1):
    if len(args) not in (2, 3):
        raise _err("idivide: usage idivide(A, B[, opt])")
    opt = "fix"
    if len(args) == 3:
        opt = getattr(args[2], "text", None)
        if opt not in ("fix", "round", "floor", "ceil"):
            raise _err("idivide: opt must be 'fix', 'round', 'floor' or 'ceil'")
    a, b = _buf("idivide", args[0]), _buf("idivide", args[1])
    dt, x, y = _pair("idivide", a, b)
    if dt is None:
        raise _err("idivide: At least one input must be an integer type.")
    info = np.iinfo(dt)

    def one(n, d):
        n = int(n) if ic.is_int(np.asarray(n)) else Fraction(float(n))
        d = int(d) if ic.is_int(np.asarray(d)) else Fraction(float(d))
        if d == 0:
            return 0 if n == 0 else (int(info.max) if n > 0 else int(info.min))
        q = Fraction(n) / Fraction(d)
        if opt == "fix":
            r = math.trunc(q)
        elif opt == "floor":
            r = math.floor(q)
        elif opt == "ceil":
            r = math.ceil(q)
        else:
            r = math.floor(abs(q) + Fraction(1, 2)) * (1 if q >= 0 else -1)
        return min(max(r, int(info.min)), int(info.max))

    out = [one(n, d) for n, d in zip(x.reshape(-1), y.reshape(-1))]
    return (NDArrayValue(np.asarray(out, dtype=object).astype(dt).reshape(x.shape)),)


def _check_double(name: str, b: np.ndarray):
    if not ic.is_int(b):
        f = np.asarray(b, dtype=np.float64)
        if np.any(f < 0) or np.any(f != np.floor(f)) or np.any(f >= _FLINT):
            raise _err(f"{name}: Double inputs must have integer values in the range of ASSUMEDTYPE.")


def _bitop(name: str, fn):
    def _f(args, *, nargout=1):
        if len(args) != 2:
            raise _err(f"{name}: requires two inputs")
        a, b = _buf(name, args[0]), _buf(name, args[1])
        dt, x, y = _pair(name, a, b)
        _check_double(name, x)
        _check_double(name, y)
        if dt is None:
            out = fn(x.astype(np.uint64), y.astype(np.uint64)).astype(np.float64)
        else:
            out = fn(ic.saturate(x, dt), ic.saturate(y, dt)).astype(dt)
        return (NDArrayValue(out),)

    return _f


def _bitshift(args, *, nargout=1):
    if len(args) != 2:
        raise _err("bitshift: usage bitshift(A, k)")
    a, k = _buf("bitshift", args[0]), _buf("bitshift", args[1])
    if a.size != 1 and k.size != 1 and a.shape != k.shape:
        raise _err("bitshift: Matrix dimensions must agree.")
    kf = np.asarray(k, dtype=np.float64)
    if np.any(kf != np.floor(kf)):
        raise _err("bitshift: K must be integer-valued")
    x, kk = np.broadcast_arrays(a, kf)
    if ic.is_int(x):
        dt = x.dtype
        bits, signed = np.iinfo(dt).bits, np.iinfo(dt).min < 0
    else:
        _check_double("bitshift", x)
        dt, bits, signed = np.float64, 53, False
    mask = (1 << bits) - 1

    def one(v, s):
        v, s = int(v), int(s)
        r = (v << s) if s >= 0 else (v >> -s)
        r &= mask
        if signed and r >= 1 << (bits - 1):
            r -= 1 << bits  # two's complement wrap
        return r

    out = [one(v, s) for v, s in zip(x.reshape(-1), kk.reshape(-1))]
    return (NDArrayValue(np.asarray(out, dtype=object).astype(dt).reshape(x.shape)),)


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        idivide=_idivide, bitshift=_bitshift,
        bitand=_bitop("bitand", np.bitwise_and),
        bitor=_bitop("bitor", np.bitwise_or),
        bitxor=_bitop("bitxor", np.bitwise_xor),
    )
