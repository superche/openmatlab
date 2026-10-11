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
    """Resolve zeros/ones/eye/nan/cell size args (scalar, m,n, or size vector)."""
    _arity(name, args, 0, 2)
    if not args:
        return (1, 1)
    if len(args) == 2:
        return (_dim(name, args[0]), _dim(name, args[1]))
    # single arg: scalar → square; size vector → MATLAB sz semantics
    b = _buf(name, args[0])
    if b.size == 1:
        n = _dim(name, args[0])
        return (n, n)
    flat = b.reshape(-1, order="F")
    if flat.size > 2:
        raise BuiltinError(
            f"{name}: N-D size vectors (numel>{2}) not supported yet"
        )
    dims: List[int] = []
    for x in flat:
        if float(x) != int(x):
            raise BuiltinError(f"{name}: size arguments must be integers")
        dims.append(max(0, int(x)))
    # numel==1 already handled above; keep defensive square if reached
    if len(dims) == 1:
        return (dims[0], dims[0])
    return (dims[0], dims[1])


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


def _inf(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    """MATLAB Inf/inf — scalar or filled array of +Inf."""
    return (_wrap(np.full(_shape2("Inf", args), np.inf)),)


def _pi(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    """MATLAB pi — ratio of circle circumference to diameter."""
    _arity("pi", args, 0, 0)
    return (_wrap(np.pi),)


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
        vals, flags = _peel_flags(name, args, {"omitnan", "includenan", "all"})
        _arity(name, vals, 1, 2)
        b = _buf(name, vals[0])
        if "all" in flags:
            flat = b.reshape(-1, order="F")
            if "omitnan" in flags or (name in ("sum", "prod", "mean") and "includenan" not in flags and np.any(np.isnan(flat))):
                # MATLAB sum omitnan by flag; default sum includes nan
                pass
            if "omitnan" in flags:
                if name == "sum":
                    return (_wrap(np.nansum(flat)),)
                if name == "prod":
                    return (_wrap(np.nanprod(flat)),)
                if name == "mean":
                    return (_wrap(np.nanmean(flat)),)
            return (_wrap(op(flat)),)
        if len(vals) == 1 and b.shape == (0, 0):
            return (_wrap(empty_value),)
        ax = _axis_arg(name, vals[1]) if len(vals) == 2 else _default_axis(b)
        if ax >= b.ndim:
            return (_wrap(b),)
        if "omitnan" in flags and name == "sum":
            return (_wrap(np.nansum(b, axis=ax, keepdims=True)),)
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
    """MATLAB-default omitnan; explicit omitnan/includenan/all flags (#69)."""
    if which == "max":
        nan_reduce = np.nanmax
        arg_op = _nan_argmax
        pair_op = np.fmax
    else:
        nan_reduce = np.nanmin
        arg_op = _nan_argmin
        pair_op = np.fmin

    def _fn(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
        vals, flags = _peel_flags(name, args, {"omitnan", "includenan", "all"})
        _arity(name, vals, 1, 3)
        use_nan = "includenan" in flags  # default omitnan
        a = _buf(name, vals[0])
        reduce_op = (np.max if which == "max" else np.min) if use_nan else nan_reduce
        if "all" in flags:
            flat = a.reshape(-1, order="F")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                with np.errstate(all="ignore"):
                    v = (np.max(flat) if which == "max" else np.min(flat)) if use_nan else nan_reduce(flat)
            return (_wrap(v),)
        if len(vals) == 2:
            if nargout > 1:
                raise BuiltinError(f"{name}: two-matrix form returns one output")
            b = _buf(name, vals[1])
            try:
                return (_wrap(pair_op(a, b)),)
            except ValueError as exc:
                raise BuiltinError(f"{name}: {exc}") from exc
        if len(vals) == 3:
            if _buf(name, vals[1]).size != 0:
                raise BuiltinError(f"{name}: use {name}(A, [], dim) for a dimension")
            ax = _axis_arg(name, vals[2])
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
                out_vals = reduce_op(a, axis=ax, keepdims=True)
        if nargout <= 1:
            return (_wrap(out_vals),)
        idx = np.expand_dims(arg_op(a, axis=ax), ax) + 1.0
        return (_wrap(out_vals), _wrap(idx))

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




def _peel_flags(name: str, args: Sequence[Value], allowed: set) -> tuple:
    """Split trailing char flags from args; return (value_args, flags_set)."""
    flags = set()
    vals = list(args)
    while vals:
        f = _char_flag(vals[-1])
        if f is None:
            break
        if f not in allowed:
            raise BuiltinError(f"{name}: unknown option '{f}'")
        flags.add(f)
        vals.pop()
    return vals, flags


def _char_flag(v: Value):
    """Return lower-cased text if v is a CharValue flag, else None."""
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue):
        return v.text.lower()
    return None


def _sort(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("sort", args, 1, 3)
    b = _buf("sort", args[0])
    descend = False
    dim_args = []
    for a in args[1:]:
        f = _char_flag(a)
        if f is None:
            dim_args.append(a)
        elif f in ("descend", "ascend"):
            descend = f == "descend"
        else:
            raise BuiltinError(f"sort: unknown option '{f}'")
    if len(dim_args) > 1:
        raise BuiltinError("sort: too many dimension arguments")
    if b.size == 0:
        empty = _wrap(b)
        return (empty,) if nargout <= 1 else (empty, empty)
    ax = _axis_arg("sort", dim_args[0]) if dim_args else _default_axis(b)
    if ax >= b.ndim:
        ones = np.ones(b.shape, dtype=np.float64)
        return (_wrap(b),) if nargout <= 1 else (_wrap(b), _wrap(ones))
    if descend:
        # stable descending: equal elements keep original order (MATLAB);
        # NaN placed first for descend (MATLAB), last for ascend.
        key = np.where(np.isnan(b), np.inf, -b)
        idx0 = np.argsort(key, axis=ax, kind="stable")
    else:
        idx0 = np.argsort(b, axis=ax, kind="stable")
    sorted_b = np.take_along_axis(b, idx0, axis=ax)
    if nargout <= 1:
        return (_wrap(sorted_b),)
    return (_wrap(sorted_b), _wrap(idx0.astype(np.float64) + 1.0))



def _find(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("find", args, 1, 3)
    b = _buf("find", args[0])
    direction = "first"
    if len(args) == 3:
        f = _char_flag(args[2])
        if f not in ("first", "last"):
            raise BuiltinError("find: direction must be 'first' or 'last'")
        direction = f
    if b.ndim != 2:
        b = np.asarray(b, dtype=np.float64)
        if b.ndim < 2:
            b = b.reshape(-1, 1)
    rows, cols = b.shape
    flat = np.asarray(b, dtype=np.float64).reshape(-1, order="F")
    # MATLAB: NaN is nonzero (isnan alone is true for find)
    mask = flat != 0
    lin0 = np.nonzero(mask)[0]
    if len(args) >= 2:
        k = _dim("find", args[1])
        lin0 = lin0[-k:] if (direction == "last" and k > 0) else lin0[:k]
    r0 = lin0 % rows if rows else lin0
    c0 = lin0 // rows if rows else lin0
    vals = flat[lin0]

    row_input = rows == 1 and cols > 1

    def colvec(data) -> NDArrayValue:
        arr = np.asarray(data, dtype=np.float64).reshape(-1)
        if arr.size == 0:
            # MATLAB: find([0 0]) → 1×0; find([]) / column → 0×1
            if row_input:
                return NDArrayValue(np.zeros((1, 0), dtype=np.float64))
            return NDArrayValue(np.zeros((0, 1), dtype=np.float64))
        if row_input:  # MATLAB: row-vector input → row-vector output
            return NDArrayValue(arr.reshape(1, -1))
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


def _unique(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    """Sorted unique; optional [C,ia,ic]=unique(A)."""
    _arity("unique", args, 1, 1)
    b = _buf("unique", args[0])
    if b.ndim == 0:
        b = b.reshape(1, 1)
    elif b.ndim == 1:
        b = b.reshape(1, -1)
    rows, cols = b.shape[:2]
    flat = np.asarray(b, dtype=np.float64).reshape(-1, order="F")
    if flat.size == 0:
        empty = NDArrayValue(np.zeros((1, 0) if rows == 1 else (0, 1), dtype=np.float64))
        if nargout <= 1:
            return (empty,)
        return (empty, empty, empty)
    u, ia0, ic0 = np.unique(flat, return_index=True, return_inverse=True)
    if rows == 1 and cols >= 1:
        C = NDArrayValue(u.reshape(1, -1))
    else:
        C = NDArrayValue(u.reshape(-1, 1))
    if nargout <= 1:
        return (C,)
    ia = NDArrayValue((ia0.astype(np.float64) + 1.0).reshape(-1, 1))
    if nargout == 2:
        return (C, ia)
    ic = NDArrayValue((ic0.astype(np.float64) + 1.0).reshape(-1, 1))
    return (C, ia, ic)


def _issorted(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    """issorted(A) / issorted(A,'descend'); matrix → all columns."""
    _arity("issorted", args, 1, 2)
    b = _buf("issorted", args[0])
    if b.ndim == 0:
        b = b.reshape(1, 1)
    elif b.ndim == 1:
        b = b.reshape(1, -1)
    descend = False
    if len(args) == 2:
        f = _char_flag(args[1])
        if f == "descend":
            descend = True
        elif f == "ascend":
            descend = False
        else:
            raise BuiltinError("issorted: flag must be 'ascend' or 'descend'")

    def _vec_sorted(v: np.ndarray) -> bool:
        if v.size <= 1:
            return True
        d = np.diff(v.astype(np.float64))
        if np.any(np.isnan(d)):
            return False
        return bool(np.all(d <= 0) if descend else np.all(d >= 0))

    if b.shape[0] == 1 or b.shape[1] == 1:
        ok = _vec_sorted(b.reshape(-1, order="F"))
    else:
        # columns
        ok = all(_vec_sorted(b[:, j]) for j in range(b.shape[1]))
    return (NDArrayValue(np.asarray([[ok]], dtype=bool)),)



def _cellfun(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    """cellfun(fh, C) or cellfun(fh, C, 'UniformOutput', false)."""
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if len(args) < 2:
        raise BuiltinError("cellfun: expected at least 2 arguments")
    fh = args[0]
    cell = args[1]
    if not isinstance(fh, FunctionHandleValue):
        raise BuiltinError("cellfun: expected function handle as first argument")
    if not isinstance(cell, CellValue):
        raise BuiltinError("cellfun: expected cell array as second argument")
    uniform = True
    i = 2
    while i < len(args):
        f = _char_flag(args[i])
        if f and f.lower() == "uniformoutput":
            if i + 1 >= len(args):
                raise BuiltinError("cellfun: UniformOutput needs a value")
            # false → 0, true → 1 / logical
            flag = args[i + 1]
            if isinstance(flag, Array):
                uniform = bool(float(np.asarray(flag.backend_buffer()).reshape(-1)[0]))
            else:
                raise BuiltinError("cellfun: UniformOutput value must be numeric/logical")
            i += 2
        else:
            raise BuiltinError(f"cellfun: unsupported option {f!r}")
    rows, cols = cell.shape
    if uniform:
        out = np.zeros((rows, cols), dtype=np.float64)
        for i in range(rows):
            for j in range(cols):
                results = fh.call([cell.get(i, j)], nargout=1)
                if not results:
                    raise BuiltinError("cellfun: function returned no outputs")
                r0 = results[0]
                if not isinstance(r0, Array):
                    raise BuiltinError("cellfun: UniformOutput requires numeric scalar")
                buf = np.asarray(r0.backend_buffer(), dtype=np.float64)
                if buf.size != 1:
                    raise BuiltinError("cellfun: UniformOutput requires numeric scalar")
                out[i, j] = float(buf.reshape(-1)[0])
        return (_wrap(out),)
    # UniformOutput false → cell of results
    grid = []
    for i in range(rows):
        row = []
        for j in range(cols):
            results = fh.call([cell.get(i, j)], nargout=1)
            row.append(results[0] if results else CellValue.empty(0, 0))
        grid.append(tuple(row))
    return (CellValue(rows=tuple(grid)),)




def _logical(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    """Cast to logical (nonzero → true)."""
    _arity("logical", args, 1, 1)
    b = _buf("logical", args[0])
    out = NDArrayValue(np.asarray(b != 0, dtype=bool))
    return (out,)


def _true_false(name: str, fill: bool):
    def _fn(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
        _arity(name, args, 0, 2)
        if not args:
            return (NDArrayValue(np.asarray([[fill]], dtype=bool)),)
        if len(args) == 1:
            b = _buf(name, args[0])
            if b.size == 1:
                n = _dim(name, args[0])
                return (NDArrayValue(np.full((n, n), fill, dtype=bool)),)
            # size vector
            flat = b.reshape(-1, order="F")
            dims = [max(0, int(x)) for x in flat[:2]]
            while len(dims) < 2:
                dims.append(1)
            return (NDArrayValue(np.full((dims[0], dims[1]), fill, dtype=bool)),)
        m, n = _dim(name, args[0]), _dim(name, args[1])
        return (NDArrayValue(np.full((m, n), fill, dtype=bool)),)

    return _fn



def _eps(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("eps", args, 0, 1)
    if not args:
        return (_wrap(np.finfo(np.float64).eps),)
    # eps(x) relative — MVP: same as eps for any x
    return (_wrap(np.finfo(np.float64).eps),)


def _realmax(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("realmax", args, 0, 0)
    return (_wrap(np.finfo(np.float64).max),)


def _realmin(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
    _arity("realmin", args, 0, 0)
    return (_wrap(np.finfo(np.float64).tiny),)



BUILTINS: Dict[str, Builtin] = {
    "zeros": _zeros,
    "ones": _ones,
    "eye": _eye,
    "linspace": _linspace,
    "nan": _nan,
    "NaN": _nan,
    "inf": _inf,
    "Inf": _inf,
    "pi": _pi,
    "cell": _cell,
    "cumsum": _cumsum,
    "sort": _sort,
    "find": _find,
    "unique": _unique,
    "issorted": _issorted,
    "cellfun": _cellfun,
    "logical": _logical,
    "eps": _eps,
    "realmax": _realmax,
    "realmin": _realmin,
    "true": _true_false("true", True),
    "false": _true_false("false", False),
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
