"""Core numeric builtins (clean-room, public MATLAB doc semantics).

Each builtin is a CallableFunction: ``fn(args, *, nargout=1) -> Sequence[Value]``.
Installed into ``FunctionResolver.builtins`` via ``register_numeric_builtins``.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Sequence
import warnings

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


def _nan(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    """MATLAB nan/NaN — scalar or filled array of NaNs (needed for omitnan max/min)."""
    return (_wrap(np.full(_shape2("nan", args), np.nan)),)


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



# ----- reductions -----


def _default_axis(b: np.ndarray) -> int:
    for ax, n in enumerate(b.shape):
        if n != 1:
            return ax
    return 0


def _axis_arg(name: str, v: Value) -> int:
    d = _dim(name, v)
    if d < 1:
        raise BuiltinError(f"{name}: dimension must be a positive integer")
    return d - 1


def _make_reduce(name: str, op, empty_value: float):
    def _fn(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
        _arity(name, args, 1, 2)
        b = _buf(name, args[0])
        if len(args) == 1 and b.shape == (0, 0):
            return (_wrap(empty_value),)
        ax = _axis_arg(name, args[1]) if len(args) == 2 else _default_axis(b)
        if ax >= b.ndim:
            return (_wrap(b),)
        return (_wrap(op(b, axis=ax, keepdims=True)),)

    return _fn


def _mean_op(b: np.ndarray, axis: int, keepdims: bool) -> np.ndarray:
    if b.shape[axis] == 0:
        shape = list(b.shape)
        shape[axis] = 1
        return np.full(shape, np.nan)
    return np.mean(b, axis=axis, keepdims=keepdims)


def _nan_argmax(a: np.ndarray, axis: int) -> np.ndarray:
    """1-based-ready 0-based index of first non-NaN max; all-NaN → 0 (→ MATLAB i=1)."""
    masked = np.where(np.isnan(a), -np.inf, a)
    return np.argmax(masked, axis=axis)


def _nan_argmin(a: np.ndarray, axis: int) -> np.ndarray:
    """1-based-ready 0-based index of first non-NaN min; all-NaN → 0 (→ MATLAB i=1)."""
    masked = np.where(np.isnan(a), np.inf, a)
    return np.argmin(masked, axis=axis)


def _make_extremum(name: str, *, which: str):
    """MATLAB-default omitnan for max/min (flag strings remain non-goals)."""
    if which == "max":
        nan_reduce = np.nanmax
        arg_op = _nan_argmax
        pair_op = np.fmax
    else:
        nan_reduce = np.nanmin
        arg_op = _nan_argmin
        pair_op = np.fmin

    def _fn(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
        _arity(name, args, 1, 3)
        a = _buf(name, args[0])
        if len(args) == 2:
            if nargout > 1:
                raise BuiltinError(f"{name}: two-matrix form returns one output")
            b = _buf(name, args[1])
            try:
                return (_wrap(pair_op(a, b)),)
            except ValueError as exc:
                raise BuiltinError(f"{name}: {exc}") from exc
        if len(args) == 3:
            if _buf(name, args[1]).size != 0:
                raise BuiltinError(f"{name}: use {name}(A, [], dim) for a dimension")
            ax = _axis_arg(name, args[2])
        else:
            ax = _default_axis(a)
        if a.size == 0:
            empty = _wrap(np.zeros((0, 0)))
            return (empty,) if nargout <= 1 else (empty, empty)
        if ax >= a.ndim:
            ones = np.ones(a.shape)
            return (_wrap(a),) if nargout <= 1 else (_wrap(a), _wrap(ones))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with np.errstate(all="ignore"):
                vals = nan_reduce(a, axis=ax, keepdims=True)
        if nargout <= 1:
            return (_wrap(vals),)
        idx = np.expand_dims(arg_op(a, axis=ax), ax) + 1.0
        return (_wrap(vals), _wrap(idx))

    return _fn



# ----- elementwise math (real domain) -----


def _matlab_round(b: np.ndarray) -> np.ndarray:
    return np.sign(b) * np.floor(np.abs(b) + 0.5)


def _make_unary(name: str, op, *, nonneg: bool = False):
    def _fn(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
        _arity(name, args, 1, 1)
        b = _buf(name, args[0])
        if nonneg and np.any(b < 0):
            raise BuiltinError(
                f"{name}: negative input needs complex results (not supported)"
            )
        with np.errstate(divide="ignore"):
            return (_wrap(op(b)),)

    return _fn


def _broadcast_pair(name: str, a: np.ndarray, b: np.ndarray):
    if a.size == 1 or b.size == 1 or a.shape == b.shape:
        return np.broadcast_arrays(a, b)
    raise BuiltinError(f"{name}: matrix dimensions must agree")


def _mod(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("mod", args, 2, 2)
    a, b = _broadcast_pair("mod", _buf("mod", args[0]), _buf("mod", args[1]))
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(b == 0, a, a - np.floor(a / np.where(b == 0, 1, b)) * b)
    return (_wrap(out),)



def _cell(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    """cell / cell(n) / cell(m,n) — empty cells of 0x0 doubles."""
    from openmatlab.runtime.cell_value import CellValue

    m, n = _shape2("cell", args)
    return (CellValue.empty(m, n),)



def _cumsum(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("cumsum", args, 1, 2)
    b = _buf("cumsum", args[0])
    if b.size == 0:
        return (_wrap(b),)
    ax = _axis_arg("cumsum", args[1]) if len(args) == 2 else _default_axis(b)
    if ax >= b.ndim:
        return (_wrap(b),)
    return (_wrap(np.cumsum(b, axis=ax)),)



def _sort(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("sort", args, 1, 2)
    b = _buf("sort", args[0])
    if b.size == 0:
        empty = _wrap(b)
        return (empty,) if nargout <= 1 else (empty, empty)
    ax = _axis_arg("sort", args[1]) if len(args) == 2 else _default_axis(b)
    if ax >= b.ndim:
        ones = np.ones(b.shape, dtype=np.float64)
        return (_wrap(b),) if nargout <= 1 else (_wrap(b), _wrap(ones))
    idx0 = np.argsort(b, axis=ax, kind="stable")
    sorted_b = np.take_along_axis(b, idx0, axis=ax)
    if nargout <= 1:
        return (_wrap(sorted_b),)
    return (_wrap(sorted_b), _wrap(idx0.astype(np.float64) + 1.0))



def _find(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("find", args, 1, 2)
    b = _buf("find", args[0])
    if b.ndim != 2:
        b = np.asarray(b, dtype=np.float64)
        if b.ndim < 2:
            b = b.reshape(-1, 1)
    rows, cols = b.shape
    flat = np.asarray(b, dtype=np.float64).reshape(-1, order="F")
    mask = (flat != 0) & ~np.isnan(flat)
    lin0 = np.nonzero(mask)[0]
    if len(args) == 2:
        k = _dim("find", args[1])
        lin0 = lin0[:k]
    r0 = lin0 % rows if rows else lin0
    c0 = lin0 // rows if rows else lin0
    vals = flat[lin0]

    def colvec(data) -> NDArrayValue:
        arr = np.asarray(data, dtype=np.float64).reshape(-1)
        if arr.size == 0:
            return NDArrayValue(np.zeros((0, 1), dtype=np.float64))
        return NDArrayValue(arr.reshape(-1, 1))

    if nargout <= 1:
        return (colvec(lin0.astype(np.float64) + 1.0),)
    if nargout == 2:
        return (colvec(r0.astype(np.float64) + 1.0), colvec(c0.astype(np.float64) + 1.0))
    return (
        colvec(r0.astype(np.float64) + 1.0),
        colvec(c0.astype(np.float64) + 1.0),
        colvec(vals),
    )


BUILTINS: Dict[str, Builtin] = {
    "zeros": _zeros,
    "ones": _ones,
    "eye": _eye,
    "linspace": _linspace,
    "nan": _nan,
    "NaN": _nan,
    "cell": _cell,
    "cumsum": _cumsum,
    "sort": _sort,
    "find": _find,
    "size": _size,
    "numel": _numel,
    "length": _length,
    "sum": _make_reduce("sum", np.sum, 0.0),
    "prod": _make_reduce("prod", np.prod, 1.0),
    "mean": _make_reduce("mean", _mean_op, float("nan")),
    "max": _make_extremum("max", which="max"),
    "min": _make_extremum("min", which="min"),
    "abs": _make_unary("abs", np.abs),
    "sqrt": _make_unary("sqrt", np.sqrt, nonneg=True),
    "exp": _make_unary("exp", np.exp),
    "log": _make_unary("log", np.log, nonneg=True),
    "sin": _make_unary("sin", np.sin),
    "cos": _make_unary("cos", np.cos),
    "floor": _make_unary("floor", np.floor),
    "ceil": _make_unary("ceil", np.ceil),
    "round": _make_unary("round", _matlab_round),
    "mod": _mod,
}


def register_numeric_builtins(resolver) -> None:
    """Install core numeric builtins into a FunctionResolver."""
    for name, fn in BUILTINS.items():
        resolver.register_builtin(name, fn)
