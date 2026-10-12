"""Class builtins: integer casts / queries, class & 'like' constructor args
(Epic #457: #72, #183). Registered into numeric_builtins.BUILTINS."""

from __future__ import annotations

from typing import Callable, Dict, Sequence

import numpy as np

from openmatlab.numerics import intclass as ic
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.value import Array, Value


def _err():
    from openmatlab.libs.numeric_builtins import BuiltinError

    return BuiltinError


def _numeric_buf(name: str, v: Value) -> np.ndarray:
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue) and not _is_string(v):
        r, c = v.shape
        return np.array([[float(ord(ch)) for ch in row] for row in v.rows]).reshape(r, c)
    if not isinstance(v, Array):
        raise _err()(f"{name}: conversion from {v.matlab_class()} is not possible")
    return np.asarray(v.backend_buffer())


def _is_string(v) -> bool:
    return getattr(v, "is_string", False)


def _to_class(buf: np.ndarray, cls: str, name: str) -> NDArrayValue:
    if cls in ic.INT_CLASSES:
        try:
            return NDArrayValue(ic.saturate(buf, ic.INT_CLASSES[cls]))
        except ic.IntClassError as exc:
            raise _err()(f"{name}: {exc}") from None
    if cls == "single":  # (#461)
        b = np.asarray(buf)
        if b.dtype == np.bool_ or ic.is_int(b):
            b = b.astype(np.float64)
        return NDArrayValue(b.astype(np.complex64 if np.iscomplexobj(b) else np.float32))
    if cls == "double":
        b = np.asarray(buf)
        return NDArrayValue(b.astype(np.complex128 if np.iscomplexobj(b) else np.float64))
    if cls == "logical":
        b = np.asarray(buf)
        if b.dtype != np.bool_ and np.any(np.isnan(b.astype(complex))):
            raise _err()("NaN's cannot be converted to logicals.")
        return NDArrayValue(b != 0)
    raise _err()(f"{name}: unsupported class '{cls}'")


def _cast_fn(cls: str):
    def _fn(args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
        if len(args) != 1:
            raise _err()(f"{cls}: expected 1 argument, got {len(args)}")
        return (_to_class(_numeric_buf(cls, args[0]), cls, cls),)

    return _fn


def _flag(v) -> str | None:
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue) and len(v.rows) <= 1:
        return v.text
    return None


def _cast(args, *, nargout=1):
    if len(args) != 2 or _flag(args[1]) is None:
        raise _err()("cast: usage cast(A, 'newclass')")
    return (_to_class(_numeric_buf("cast", args[0]), _flag(args[1]), "cast"),)


def _intlimit(which: str):
    def _fn(args, *, nargout=1):
        cls = "int32" if not args else _flag(args[0])
        if args and not isinstance(args[0], Array) and cls is None:
            raise _err()(f"{which}: argument must be a class name")
        if args and isinstance(args[0], Array):
            cls = args[0].matlab_class()  # intmax(x) uses x's class
        if cls not in ic.INT_CLASSES:
            raise _err()(f"{which}: invalid class name '{cls}'")
        info = np.iinfo(ic.INT_CLASSES[cls])
        v = info.max if which == "intmax" else info.min
        return (NDArrayValue(np.array([[v]], dtype=ic.INT_CLASSES[cls])),)

    return _fn


def _is_cls(name: str, pred: Callable[[str], bool]):
    def _fn(args, *, nargout=1):
        if len(args) != 1:
            raise _err()(f"{name}: expected 1 argument")
        return (NDArrayValue(np.array([[pred(args[0].matlab_class())]])),)

    return _fn


def _isa(args, *, nargout=1):
    if len(args) != 2 or _flag(args[1]) is None:
        raise _err()("isa: usage isa(obj, 'classname')")
    c, want = args[0].matlab_class(), _flag(args[1])
    groups = {
        "numeric": ("double", "single", *ic.INT_CLASSES),
        "float": ("double", "single"),
        "integer": tuple(ic.INT_CLASSES),
    }
    return (NDArrayValue(np.array([[c in groups.get(want, (want,))]])),)


# ----- 'like' / class trailing args for constructors (#183) -----

def _peel_class(name: str, args: Sequence[Value], allowed: tuple):
    """Split trailing ('like', P) or 'classname'. Returns (args, cls, complex)."""
    args = list(args)
    if len(args) >= 2 and (_flag(args[-2]) or "").lower() == "like":
        proto = args[-1]
        if not isinstance(proto, Array):
            raise _err()(f"{name}: 'like' prototype must be numeric or logical")
        b = np.asarray(proto.backend_buffer())
        return args[:-2], proto.matlab_class(), bool(np.iscomplexobj(b))
    if args and _flag(args[-1]) is not None:
        cls = _flag(args[-1])
        if cls not in allowed:
            raise _err()(f"{name}: class '{cls}' is not supported")
        return args[:-1], cls, False
    return args, None, False


def _with_class(name: str, fn, allowed: tuple):
    def _wrapped(args, *, nargout=1):
        rest, cls, cplx = _peel_class(name, args, allowed)
        out = fn(rest, nargout=nargout)
        if cls is None:
            return out
        if cls not in allowed:
            raise _err()(f"{name}: 'like' a {cls} prototype is not supported")
        v = _to_class(np.asarray(out[0].backend_buffer()), cls, name)
        if cplx and cls == "double":
            v = NDArrayValue(np.asarray(v.backend_buffer(), dtype=np.complex128))
        return (v, *out[1:])

    return _wrapped


_NUMERIC = ("double", "single", *ic.INT_CLASSES)


def _single_first(args, out):
    """A single input keeps single for the first output (#461)."""
    if args and isinstance(args[0], Array) and out and isinstance(out[0], Array):
        if np.asarray(args[0].backend_buffer()).dtype in (np.float32, np.complex64):
            b = np.asarray(out[0].backend_buffer())
            if b.dtype in (np.float64, np.complex128):
                b = b.astype(np.complex64 if np.iscomplexobj(b) else np.float32)
                return (NDArrayValue(b), *out[1:])
    return out


def _keep_single(fn):
    def _wrapped(args, *, nargout=1):
        return _single_first(args, fn(args, nargout=nargout))

    return _wrapped


_SINGLE_UNARY = (
    "sqrt", "exp", "log", "log10", "sin", "cos", "tan", "sinh", "cosh", "tanh", "asin",
    "acos", "atan", "asinh", "acosh", "atanh", "floor", "ceil", "round", "fix", "real",
    "imag", "conj", "angle", "mean", "transpose", "reshape", "repmat", "mod", "rem",
    "permute", "flip", "fliplr", "flipud", "circshift", "diff", "cumprod", "full",
)


def _keep_int(fn):
    """sum/prod/max/min/abs/cumsum/sort/unique keep an integer input's class."""

    def _wrapped(args, *, nargout=1):
        out = fn(args, nargout=nargout)
        if args and isinstance(args[0], Array) and ic.is_int(args[0].backend_buffer()):
            dt = np.asarray(args[0].backend_buffer()).dtype
            first = out[0]
            if isinstance(first, Array):
                return (NDArrayValue(ic.saturate(np.asarray(first.backend_buffer()), dt)), *out[1:])
        return _single_first(args, out)

    return _wrapped


# ----- string scalars (#78) -----

def _string(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue, StringValue

    if len(args) != 1:
        raise _err()("string: expected 1 argument")
    v = args[0]
    if isinstance(v, CharValue):
        if len(v.rows) > 1:
            raise _err()("string: multi-row char needs string arrays (not supported yet)")
        return (StringValue(v.text),)
    if isinstance(v, Array) and v.numel() == 1:
        x = np.asarray(v.backend_buffer()).reshape(-1)[0]
        if np.iscomplexobj(x):
            raise _err()("string: complex input is not supported yet")
        if isinstance(x, (bool, np.bool_)):
            return (StringValue("true" if x else "false"),)
        x = float(x)
        if x != x:
            return (StringValue("NaN"),)
        if x == int(x) and abs(x) < 1e15:
            return (StringValue(str(int(x))),)
        return (StringValue(f"{x:.4f}".rstrip("0")),)
    raise _err()("string: only scalars are supported (string arrays: residual of #457)")


def _strlength(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue

    if len(args) != 1 or not isinstance(args[0], CharValue):
        raise _err()("strlength: argument must be a string or character vector")
    return (NDArrayValue(np.array([[float(len(args[0].text))]])),)


def _isstring(args, *, nargout=1):
    if len(args) != 1:
        raise _err()("isstring: expected 1 argument")
    return (NDArrayValue(np.array([[bool(getattr(args[0], "is_string", False))]])),)


def _string_aware_double(old):
    """double("3.5") parses the text (MATLAB str2double); char/num unchanged."""

    def _fn(args, *, nargout=1):
        if len(args) == 1 and getattr(args[0], "is_string", False):
            try:
                return (NDArrayValue(np.array([[float(args[0].text.strip())]])),)
            except ValueError:
                return (NDArrayValue(np.array([[np.nan]])),)
        return old(args, nargout=nargout)

    return _fn


def register(builtins: Dict[str, Callable]) -> None:
    builtins["string"] = _string
    builtins["strlength"] = _strlength
    builtins["isstring"] = _isstring
    builtins["double"] = _string_aware_double(builtins["double"])
    for cls in ic.INT_CLASSES:
        builtins[cls] = _cast_fn(cls)
    builtins["single"] = _cast_fn("single")
    builtins["cast"] = _cast
    builtins["intmax"] = _intlimit("intmax")
    builtins["intmin"] = _intlimit("intmin")
    builtins["isinteger"] = _is_cls("isinteger", lambda c: c in ic.INT_CLASSES)
    builtins["isfloat"] = _is_cls("isfloat", lambda c: c in ("double", "single"))
    builtins["isnumeric"] = _is_cls("isnumeric", lambda c: c in _NUMERIC or c == "single")
    builtins["isa"] = _isa
    for k in ("zeros", "ones", "eye"):
        builtins[k] = _with_class(k, builtins[k], _NUMERIC)
    for k in ("nan", "NaN", "inf", "Inf"):
        builtins[k] = _with_class(k, builtins[k], ("double", "single"))
    for k in ("true", "false"):
        builtins[k] = _with_class(k, builtins[k], ("logical",))
    for k in ("sum", "prod", "max", "min", "abs", "cumsum", "sort", "unique"):
        builtins[k] = _keep_int(builtins[k])
    for k in _SINGLE_UNARY:
        if k in builtins:
            builtins[k] = _keep_single(builtins[k])
