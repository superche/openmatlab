"""permute / ipermute / flip / fliplr / flipud / circshift (#442, #445)."""

from __future__ import annotations

from typing import Callable, Dict, Sequence

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.value import Array, Value


def _err(msg: str):
    from openmatlab.libs.numeric_builtins import BuiltinError

    return BuiltinError(msg)


def _arr(name: str, v: Value) -> np.ndarray:
    if not isinstance(v, Array):
        raise _err(f"{name}: expected a numeric or logical array")
    return np.asarray(v.backend_buffer())


def _ints(name: str, v: Value) -> list:
    b = _arr(name, v).reshape(-1)
    if np.any(b != np.floor(b.real)):
        raise _err(f"{name}: values must be integers")
    return [int(x) for x in b.real]


def _first_nonsingleton(a: np.ndarray) -> int:
    for ax, n in enumerate(a.shape):
        if n != 1:
            return ax
    return 0


def _order(name: str, a: np.ndarray, v: Value) -> tuple:
    order = _ints(name, v)
    n = len(order)
    if sorted(order) != list(range(1, n + 1)) or n < a.ndim:
        raise _err(f"{name}: ORDER must be a permutation of 1..N with N >= ndims(A)")
    return a.reshape(a.shape + (1,) * (n - a.ndim)), [k - 1 for k in order]


def _permute(args, *, nargout=1):
    if len(args) != 2:
        raise _err("permute: usage permute(A, order)")
    a, order = _order("permute", _arr("permute", args[0]), args[1])
    return (NDArrayValue(np.ascontiguousarray(np.transpose(a, order))),)


def _ipermute(args, *, nargout=1):
    if len(args) != 2:
        raise _err("ipermute: usage ipermute(A, order)")
    a, order = _order("ipermute", _arr("ipermute", args[0]), args[1])
    return (NDArrayValue(np.ascontiguousarray(np.transpose(a, np.argsort(order)))),)


def _flip_axis(name: str, a: np.ndarray, ax: int) -> NDArrayValue:
    if ax >= a.ndim:
        return NDArrayValue(a.copy())
    return NDArrayValue(np.ascontiguousarray(np.flip(a, axis=ax)))


def _flip(args, *, nargout=1):
    if len(args) not in (1, 2):
        raise _err("flip: usage flip(A) or flip(A, dim)")
    a = _arr("flip", args[0])
    ax = _ints("flip", args[1])[0] - 1 if len(args) == 2 else _first_nonsingleton(a)
    if ax < 0:
        raise _err("flip: dimension must be a positive integer")
    return (_flip_axis("flip", a, ax),)


def _fixed_flip(name: str, ax: int):
    def _fn(args, *, nargout=1):
        if len(args) != 1:
            raise _err(f"{name}: expected 1 argument")
        return (_flip_axis(name, _arr(name, args[0]), ax),)

    return _fn


def _circshift(args, *, nargout=1):
    if len(args) not in (2, 3):
        raise _err("circshift: usage circshift(A, K) or circshift(A, K, dim)")
    a = _arr("circshift", args[0])
    k = _ints("circshift", args[1])
    if len(args) == 3:
        dims = [_ints("circshift", args[2])[0] - 1]
        if len(k) != 1:
            raise _err("circshift: K must be a scalar when dim is given")
    elif len(k) == 1:
        dims = [_first_nonsingleton(a)]
    else:
        dims = list(range(len(k)))
    out = a.reshape(a.shape + (1,) * max(0, max(dims) + 1 - a.ndim))
    out = np.roll(out, k, axis=dims) if len(dims) > 1 else np.roll(out, k[0], axis=dims[0])
    return (NDArrayValue(np.ascontiguousarray(out)),)


def _equal(a: Value, b: Value) -> bool:
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(a, CellValue) or isinstance(b, CellValue):
        if not (isinstance(a, CellValue) and isinstance(b, CellValue)):
            return False
        return a.shape == b.shape and all(
            _equal(x, y) for ra, rb in zip(a.rows, b.rows) for x, y in zip(ra, rb)
        )
    if isinstance(a, Array) and isinstance(b, Array):
        x, y = np.asarray(a.backend_buffer()), np.asarray(b.backend_buffer())
        if x.shape != y.shape:
            return False
        return bool(np.all(x == y))
    return a == b


def _isequal(args, *, nargout=1):
    """isequal(A, B, ...) - class-insensitive value/size equality; NaN ~= NaN (#471)."""
    if len(args) < 2:
        raise _err("isequal: requires at least two inputs")
    ok = all(_equal(args[0], b) for b in args[1:])
    return (NDArrayValue(np.array([[ok]])),)


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        permute=_permute, ipermute=_ipermute, flip=_flip, circshift=_circshift,
        isequal=_isequal, fliplr=_fixed_flip("fliplr", 1), flipud=_fixed_flip("flipud", 0),
    )
