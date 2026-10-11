"""Core numeric builtins (clean-room, public MATLAB doc semantics).

Each builtin is a CallableFunction: ``fn(args, *, nargout=1) -> Sequence[Value]``.
Installed into ``FunctionResolver.builtins`` via ``register_numeric_builtins``.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Sequence

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.value import Array, Value


class BuiltinError(ValueError):
    """Argument / shape error inside a numeric builtin."""


Builtin = Callable[..., Sequence[Value]]


def _wrap(data: object) -> NDArrayValue:
    arr = np.asarray(data, dtype=np.float64)
    if arr.ndim == 0:
        arr = arr.reshape(1, 1)
    elif arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return NDArrayValue(arr)


def _buf(name: str, v: Value) -> np.ndarray:
    if not isinstance(v, Array):
        raise BuiltinError(f"{name}: expected numeric Array argument")
    return np.asarray(v.backend_buffer(), dtype=np.float64)


def _scalar(name: str, v: Value) -> float:
    b = _buf(name, v)
    if b.size != 1:
        raise BuiltinError(f"{name}: expected scalar argument")
    return float(b.reshape(-1)[0])


def _dim(name: str, v: Value) -> int:
    x = _scalar(name, v)
    if x != int(x):
        raise BuiltinError(f"{name}: size arguments must be integers")
    return max(0, int(x))


def _arity(name: str, args: Sequence[Value], lo: int, hi: int) -> None:
    if not lo <= len(args) <= hi:
        raise BuiltinError(f"{name}: expected {lo}..{hi} arguments, got {len(args)}")


def _shape2(name: str, args: Sequence[Value]) -> tuple:
    _arity(name, args, 0, 2)
    if not args:
        return (1, 1)
    if len(args) == 1:
        n = _dim(name, args[0])
        return (n, n)
    return (_dim(name, args[0]), _dim(name, args[1]))


# ----- constructors -----


def _zeros(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    return (_wrap(np.zeros(_shape2("zeros", args))),)


def _ones(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    return (_wrap(np.ones(_shape2("ones", args))),)


def _eye(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    m, n = _shape2("eye", args)
    return (_wrap(np.eye(m, n)),)


def _linspace(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("linspace", args, 2, 3)
    a = _scalar("linspace", args[0])
    b = _scalar("linspace", args[1])
    n = _dim("linspace", args[2]) if len(args) == 3 else 100
    return (_wrap(np.linspace(a, b, n).reshape(1, n)),)


# ----- shape queries -----


def _size(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("size", args, 1, 2)
    shape = tuple(_buf("size", args[0]).shape) or (1, 1)
    if len(args) == 2:
        d = _dim("size", args[1])
        if d < 1:
            raise BuiltinError("size: dimension must be a positive integer")
        return (_wrap(shape[d - 1] if d <= len(shape) else 1),)
    if nargout <= 1:
        return (_wrap(list(shape)),)
    outs: List[Value] = [_wrap(s) for s in shape[: nargout - 1]]
    # last output absorbs remaining dims (product), per MATLAB
    rest = shape[nargout - 1 :]
    outs.append(_wrap(int(np.prod(rest)) if rest else 1))
    return tuple(outs)


def _numel(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("numel", args, 1, 1)
    return (_wrap(_buf("numel", args[0]).size),)


def _length(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("length", args, 1, 1)
    b = _buf("length", args[0])
    return (_wrap(0 if b.size == 0 else max(b.shape)),)


BUILTINS: Dict[str, Builtin] = {
    "zeros": _zeros,
    "ones": _ones,
    "eye": _eye,
    "linspace": _linspace,
    "size": _size,
    "numel": _numel,
    "length": _length,
}


def register_numeric_builtins(resolver) -> None:
    """Install core numeric builtins into a FunctionResolver."""
    for name, fn in BUILTINS.items():
        resolver.register_builtin(name, fn)
