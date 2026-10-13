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


# --- #488 residuals: spalloc / spdiags / sprand / spfun ---------------------

def _spalloc(args, *, nargout=1):
    if len(args) not in (2, 3):
        raise _err("spalloc: usage spalloc(m, n, nz)")
    m, n = _dim("spalloc", args[0]), _dim("spalloc", args[1])
    if len(args) == 3:
        _dim("spalloc", args[2])  # capacity hint; storage is dense (see design doc)
    return (SparseValue(np.zeros((m, n))),)


def _diag_index(k: int, m: int, n: int):
    """Rows/cols of diagonal k in an m x n matrix, plus the B row index MATLAB uses."""
    i = np.arange(max(0, -k), min(m, n - k))
    j = i + k
    # MATLAB: for m >= n, B(j, :) aligns with columns; for m < n, with rows.
    b = j if m >= n else i
    return i, j, b


def _spdiags(args, *, nargout=1):
    if len(args) == 4:  # S = spdiags(B, d, m, n)
        B = _num("spdiags", args[0])
        d = _num("spdiags", args[1]).reshape(-1).real.astype(int)
        m, n = _dim("spdiags", args[2]), _dim("spdiags", args[3])
        if B.ndim < 2:
            B = B.reshape(-1, 1)
        elif d.size == 1 and B.shape[0] == 1:
            B = B.reshape(-1, 1)  # a row vector of values for one diagonal
        if B.size == 1:
            B = np.full((max(m, n), d.size), B.reshape(-1)[0])
        if B.shape[1] != d.size:
            raise _err("spdiags: B must have one column per diagonal")
        out = np.zeros((m, n), dtype=np.result_type(B, np.float64))
        for c, k in enumerate(d):
            i, j, b = _diag_index(int(k), m, n)
            ok = b < B.shape[0]
            out[i[ok], j[ok]] = B[b[ok], c]
        return (SparseValue(out),)
    if len(args) in (1, 2):  # B = spdiags(A[, d]), [B, d] = spdiags(A)
        A = _num("spdiags", args[0])
        A = A.reshape(1, 1) if A.ndim == 0 else A
        m, n = A.shape
        if len(args) == 2:
            d = _num("spdiags", args[1]).reshape(-1).real.astype(int)
        else:
            d = np.array([k for k in range(-(m - 1), n) if np.any(np.diagonal(A, k))], dtype=int)
        out = np.zeros((min(m, n), d.size), dtype=A.dtype if A.dtype != np.bool_ else np.float64)
        for c, k in enumerate(d):
            i, j, b = _diag_index(int(k), m, n)
            out[b, c] = A[i, j]
        res = [NDArrayValue(out)]
        if nargout > 1:
            res.append(NDArrayValue(d.reshape(-1, 1).astype(float)))
        return tuple(res)
    raise _err("spdiags: usage spdiags(B, d, m, n) or spdiags(A[, d])")


def _sprand(args, *, nargout=1):
    if len(args) == 1:  # same sparsity pattern as S, uniform random values
        A = _num("sprand", args[0])
        A = A.reshape(1, 1) if A.ndim == 0 else A
        out = np.where(A != 0, np.random.random_sample(A.shape), 0.0)
        return (SparseValue(out),)
    if len(args) != 3:
        raise _err("sprand: usage sprand(m, n, density) or sprand(S)")
    m, n = _dim("sprand", args[0]), _dim("sprand", args[1])
    dens = float(_num("sprand", args[2]).reshape(-1)[0].real)
    if not 0 <= dens <= 1:
        raise _err("sprand: density must be between 0 and 1")
    flat = np.zeros(m * n)
    k = int(round(dens * m * n))
    if k:
        flat[np.random.choice(m * n, size=k, replace=False)] = np.random.random_sample(k)
    out = flat.reshape((m, n), order="F")
    return (SparseValue(out),)


def _spfun(args, *, nargout=1):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if len(args) != 2 or not isinstance(args[0], FunctionHandleValue):
        raise _err("spfun: usage spfun(fh, S)")
    A = _num("spfun", args[1])
    A = A.reshape(1, 1) if A.ndim == 0 else A
    rows, cols = np.nonzero(A.T)  # column-major order of nonzeros
    rows, cols = cols, rows
    vals = A[rows, cols].reshape(-1, 1)
    res = args[0].call([NDArrayValue(vals.astype(np.float64) if vals.dtype == np.bool_ else vals)], nargout=1)
    if not res or not isinstance(res[0], Array) or res[0].numel() != vals.size:
        raise _err("spfun: function must return one value per nonzero element")
    rv = np.asarray(res[0].backend_buffer()).reshape(-1)
    out = np.zeros(A.shape, dtype=np.result_type(rv, np.float64))
    out[rows, cols] = rv
    return (SparseValue(out),)


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        sparse=_sparse, full=_full, issparse=_issparse, nnz=_nnz, nonzeros=_nonzeros,
        nzmax=_nnz, speye=_speye, spones=_spones,
        spalloc=_spalloc, spdiags=_spdiags, sprand=_sprand, spfun=_spfun,
    )
    for k in _ZERO_PRESERVING:
        if k in builtins:
            builtins[k] = _keep_sparse(builtins[k])
