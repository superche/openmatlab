"""sparse / full / issparse / nnz / nonzeros / nzmax / speye / spones (#451)."""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics import intclass as ic
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.numerics.sparse import SparseValue, is_sparse, to_sparse
from openmatlab.runtime.value import Array, Value


def _err(msg: str):
    from openmatlab.libs.numeric_builtins import BuiltinError

    return BuiltinError(msg)


def _num(name: str, v: Value) -> np.ndarray:
    if not isinstance(v, Array):
        raise _err(f"Undefined function '{name}' for input arguments of type '{v.matlab_class()}'.")
    b = np.asarray(v.backend_buffer())
    if ic.is_int(b) or b.dtype in (np.float32, np.complex64):
        raise _err(f"Undefined function '{name}' for input arguments of type '{v.matlab_class()}'.")
    return b


def _dim(name: str, v: Value) -> int:
    b = _num(name, v).reshape(-1)
    if b.size != 1 or b[0] != np.floor(b[0].real) or b[0].real < 0:
        raise _err(f"{name}: size arguments must be non-negative integers")
    return int(b[0].real)


def _sparse(args, *, nargout=1):
    if len(args) == 1:
        b = _num("sparse", args[0])
        if b.ndim > 2:
            raise _err("sparse: N-dimensional sparse arrays are not supported.")
        if b.dtype != np.bool_:
            b = b.astype(np.complex128 if np.iscomplexobj(b) else np.float64)
        return (to_sparse(b.copy()),)
    if len(args) == 2:
        return (to_sparse(np.zeros((_dim("sparse", args[0]), _dim("sparse", args[1])))),)
    if len(args) not in (3, 5, 6):
        raise _err("sparse: usage sparse(A), sparse(m,n), sparse(i,j,v[,m,n[,nz]])")
    i, j, v = (_num("sparse", a).reshape(-1, order="F") for a in args[:3])
    n = max(i.size, j.size, v.size)
    for x in (i, j, v):
        if x.size not in (1, n):
            raise _err("sparse: Vectors must be the same lengths.")
    i, j, v = (np.broadcast_to(x, (n,)) for x in (i, j, v))
    for x in (i, j):
        if x.size and (np.any(x != np.floor(x.real)) or np.any(x.real < 1)):
            raise _err("sparse: Index into matrix must be positive.")
    ii, jj = i.real.astype(np.int64) - 1, j.real.astype(np.int64) - 1
    if len(args) >= 5:
        m, k = _dim("sparse", args[3]), _dim("sparse", args[4])
        if n and (ii.max() >= m or jj.max() >= k):
            raise _err("sparse: Index exceeds matrix dimensions.")
    else:
        m, k = (int(ii.max()) + 1, int(jj.max()) + 1) if n else (0, 0)
    if v.dtype == np.bool_:
        out = np.zeros((m, k), dtype=bool)
        np.logical_or.at(out, (ii, jj), v)
    else:
        out = np.zeros((m, k), dtype=np.complex128 if np.iscomplexobj(v) else np.float64)
        np.add.at(out, (ii, jj), v)  # duplicates add (MATLAB)
        if np.iscomplexobj(out) and not np.any(out.imag):
            out = out.real.copy()
    return (to_sparse(out),)


def _full(args, *, nargout=1):
    if len(args) != 1:
        raise _err("full: expected 1 argument")
    v = args[0]
    if is_sparse(v):
        return (NDArrayValue(np.array(v.backend_buffer())),)
    return (v,)


def _issparse(args, *, nargout=1):
    if len(args) != 1:
        raise _err("issparse: expected 1 argument")
    return (NDArrayValue(np.array([[is_sparse(args[0])]])),)


def _nnz(args, *, nargout=1):
    if len(args) != 1 or not isinstance(args[0], Array):
        raise _err("nnz: expected one numeric or logical argument")
    return (NDArrayValue(np.array([[float(np.count_nonzero(args[0].backend_buffer()))]])),)


def _nonzeros(args, *, nargout=1):
    if len(args) != 1 or not isinstance(args[0], Array):
        raise _err("nonzeros: expected one numeric or logical argument")
    b = np.asarray(args[0].backend_buffer()).reshape(-1, order="F")
    return (NDArrayValue(b[b != 0].reshape(-1, 1).copy()),)


def _speye(args, *, nargout=1):
    if len(args) > 2:
        raise _err("speye: usage speye(n) or speye(m,n)")
    if not args:
        m = n = 1
    elif len(args) == 1:
        b = _num("speye", args[0]).reshape(-1)
        m, n = (int(b[0]), int(b[0])) if b.size == 1 else (int(b[0]), int(b[1]))
    else:
        m, n = _dim("speye", args[0]), _dim("speye", args[1])
    return (to_sparse(np.eye(m, n)),)


def _spones(args, *, nargout=1):
    if len(args) != 1:
        raise _err("spones: expected 1 argument")
    b = _num("spones", args[0])
    return (to_sparse((b != 0).astype(np.float64)),)


def _keep_sparse(fn):
    """Zero-preserving builtins return sparse for sparse input (MATLAB)."""

    def _wrapped(args, *, nargout=1):
        out = fn(args, nargout=nargout)
        if args and is_sparse(args[0]) and out and isinstance(out[0], NDArrayValue):
            return (to_sparse(out[0].backend_buffer()), *out[1:])
        return out

    return _wrapped


_ZERO_PRESERVING = (
    "abs", "sqrt", "sin", "tan", "sinh", "tanh", "asin", "atan", "asinh", "atanh", "floor", "ceil",
    "round", "fix", "real", "imag", "conj", "sum", "max", "min", "cumsum", "transpose", "reshape",
    "logical", "double", "mean", "flip", "fliplr", "flipud", "circshift", "permute",
)


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        sparse=_sparse, full=_full, issparse=_issparse, nnz=_nnz, nonzeros=_nonzeros,
        nzmax=_nnz, speye=_speye, spones=_spones,
    )
    for k in _ZERO_PRESERVING:
        if k in builtins:
            builtins[k] = _keep_sparse(builtins[k])
