"""sparse / full / issparse / nnz / nonzeros / nzmax / speye / spones (#451)."""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics import intclass as ic
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.numerics.sparse import SparseValue, is_sparse, to_sparse
from openmatlab.numerics.sparse_store import Store
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
    if len(args) == 1 and is_sparse(args[0]):
        return (SparseValue(args[0].store),)
    if len(args) == 1:
        b = _num("sparse", args[0])
        if b.ndim > 2:
            raise _err("sparse: N-dimensional sparse arrays are not supported.")
        if b.dtype != np.bool_:
            b = b.astype(np.complex128 if np.iscomplexobj(b) else np.float64)
        return (to_sparse(b.copy()),)
    if len(args) == 2:
        return (SparseValue(Store.zeros(_dim("sparse", args[0]), _dim("sparse", args[1]))),)
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
    if v.dtype == np.bool_:  # duplicates OR (logical)
        return (SparseValue(Store(m, k, ii, jj, v, dtype=np.bool_)),)
    dt = np.complex128 if np.iscomplexobj(v) else np.float64
    st = Store(m, k, ii, jj, v.astype(dt), dtype=dt)  # duplicates add (MATLAB)
    if dt == np.complex128 and not np.any(st.data.imag):
        st = st.astype(np.float64)
    return (SparseValue(st),)


def _full(args, *, nargout=1):
    if len(args) != 1:
        raise _err("full: expected 1 argument")
    v = args[0]
    if is_sparse(v):
        return (NDArrayValue(v.store.to_dense()),)
    return (v,)


def _issparse(args, *, nargout=1):
    if len(args) != 1:
        raise _err("issparse: expected 1 argument")
    return (NDArrayValue(np.array([[is_sparse(args[0])]])),)


def _nnz(args, *, nargout=1):
    if len(args) != 1 or not isinstance(args[0], Array):
        raise _err("nnz: expected one numeric or logical argument")
    if is_sparse(args[0]):
        return (NDArrayValue(np.array([[float(args[0].store.nnz)]])),)
    return (NDArrayValue(np.array([[float(np.count_nonzero(args[0].backend_buffer()))]])),)


def _nonzeros(args, *, nargout=1):
    if len(args) != 1 or not isinstance(args[0], Array):
        raise _err("nonzeros: expected one numeric or logical argument")
    if is_sparse(args[0]):
        return (NDArrayValue(args[0].store.data.reshape(-1, 1).copy()),)
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
    return (SparseValue(Store.eye(m, n)),)


def _spones(args, *, nargout=1):
    if len(args) != 1:
        raise _err("spones: expected 1 argument")
    if is_sparse(args[0]):
        st = args[0].store
        return (SparseValue(st.with_data(np.ones(st.nnz), np.float64)),)
    b = _num("spones", args[0])
    return (to_sparse((b != 0).astype(np.float64)),)


def _round_half_away(x):
    if np.iscomplexobj(x):
        return _round_half_away(x.real) + 1j * _round_half_away(x.imag)
    return np.sign(x) * np.floor(np.abs(x) + 0.5)


def _real_in(lo, hi):
    def ok(d):
        return d.dtype != np.complex128 and bool(np.all((d >= lo) & (d <= hi)))
    return ok


_NATIVE_MAP = {
    "abs": (np.abs, None), "sqrt": (np.sqrt, _real_in(0, np.inf)), "sin": (np.sin, None),
    "tan": (np.tan, None), "sinh": (np.sinh, None), "tanh": (np.tanh, None),
    "asin": (np.arcsin, _real_in(-1, 1)), "atan": (np.arctan, None), "asinh": (np.arcsinh, None),
    "atanh": (np.arctanh, _real_in(-1, 1)), "floor": (np.floor, None), "ceil": (np.ceil, None),
    "round": (_round_half_away, None), "fix": (np.trunc, None), "real": (np.real, None),
    "imag": (np.imag, None), "conj": (np.conj, None),
}


def _sum_dim(st, args):
    if len(args) == 1:
        return 1 if st.m == 1 and st.n != 1 else 0
    if len(args) == 2 and isinstance(args[1], NDArrayValue) and not is_sparse(args[1]):
        b = np.asarray(args[1].backend_buffer()).reshape(-1)
        if b.size == 1 and b.dtype != object and b[0] in (1, 2):
            return int(b[0]) - 1
    return None


def _scalars(vals):
    out = []
    for v in vals:
        if not isinstance(v, NDArrayValue) or is_sparse(v):
            return None
        b = np.asarray(v.backend_buffer()).reshape(-1)
        if b.dtype == object or np.iscomplexobj(b) or np.any(b != np.floor(b)):
            return None
        out.extend(int(x) for x in b)
    return out


def _reshape_dims(rest):
    d = _scalars(rest)
    if d is None or len(d) != 2 or min(d) < 0:
        return None
    return d


def _cumsum(st, ax):
    t = st if ax == 0 else st.transpose()
    d = t.data.astype(np.float64) if t.dtype == np.bool_ else t.data
    R, C, V = [], [], []
    ptr = t.indptr
    for j in np.nonzero(np.diff(ptr))[0]:
        lo, hi = ptr[j], ptr[j + 1]
        rr = t.rows[lo:hi]
        acc = np.zeros(t.m - rr[0], dtype=d.dtype)
        acc[rr - rr[0]] = d[lo:hi]
        acc = np.cumsum(acc)
        R.append(np.arange(rr[0], t.m)); C.append(np.full(acc.size, j)); V.append(acc)
    if not R:
        out = Store.zeros(t.m, t.n, d.dtype)
    else:
        out = Store(t.m, t.n, np.concatenate(R), np.concatenate(C), np.concatenate(V), dtype=d.dtype)
    return out if ax == 0 else out.transpose()


def _flip(st, ax):
    if ax == 0:
        return Store(st.m, st.n, st.m - 1 - st.rows, st.cols, st.data, dtype=st.dtype)
    return Store(st.m, st.n, st.rows, st.n - 1 - st.cols, st.data, dtype=st.dtype)


def _circshift(st, args):
    k = _scalars(args[1:2])
    if k is None or len(args) > 3:
        return None
    if len(args) == 3:
        dim = _scalars(args[2:3])
        if dim is None or len(dim) != 1 or dim[0] not in (1, 2) or len(k) != 1:
            return None
        k = [k[0], 0] if dim[0] == 1 else [0, k[0]]
    elif len(k) == 1:
        k = [0, k[0]] if (st.m == 1 and st.n != 1) else [k[0], 0]
    if len(k) != 2:
        return None
    r = (st.rows + k[0]) % st.m if st.m else st.rows
    c = (st.cols + k[1]) % st.n if st.n else st.cols
    return SparseValue(Store(st.m, st.n, r, c, st.data, dtype=st.dtype))


def native_sparse_call(name, args, nargout):
    """Compressed-storage implementation of a zero-preserving builtin, or None (#516)."""
    if not args or not is_sparse(args[0]) or nargout > 1:
        return None
    st = args[0].store
    if name in _NATIVE_MAP and len(args) == 1:
        fn, ok = _NATIVE_MAP[name]
        if st.dtype == np.bool_ and name in ("real", "imag", "conj"):
            return None
        if ok is not None and not ok(st.data.astype(np.float64) if st.dtype == np.bool_ else st.data):
            return None
        r = st.map(fn)
        if r is not None and name in ("real", "imag", "abs"):
            r = r.astype(np.float64)
        return None if r is None else SparseValue(r)
    if name == "transpose" and len(args) == 1:
        return SparseValue(st.transpose())
    if name == "double" and len(args) == 1:
        return SparseValue(st.astype(np.float64))
    if name == "logical" and len(args) == 1:
        if st.dtype != np.bool_ and (st.dtype == np.complex128 or np.any(np.isnan(st.data))):
            return None
        return SparseValue(st.astype(np.bool_))
    if name == "sum":
        ax = _sum_dim(st, args)
        if ax is None or st.dtype == np.bool_ and False:
            return None
        return SparseValue(st.sum(ax))
    if name == "mean":
        ax = _sum_dim(st, args)
        if ax is None or (st.m == 0 or st.n == 0):
            return None
        r = st.sum(ax)
        return SparseValue(r.with_data(r.data / (st.m if ax == 0 else st.n)))
    if name == "cumsum":
        ax = _sum_dim(st, args)
        return None if ax is None else SparseValue(_cumsum(st, ax))
    if name == "reshape":
        dims = _reshape_dims(args[1:])
        if dims is None or dims[0] * dims[1] != st.m * st.n:
            return None
        return SparseValue(st.reshape(*dims))
    if name in ("flipud", "fliplr", "flip"):
        if name == "flip":
            ax = _sum_dim(st, args)
        else:
            ax = 0 if name == "flipud" else 1
            if len(args) != 1:
                return None
        if ax is None:
            return None
        return SparseValue(_flip(st, ax))
    if name == "circshift":
        return _circshift(st, args)
    if name == "permute" and len(args) == 2:
        p = np.asarray(args[1].backend_buffer()).reshape(-1).tolist() if isinstance(args[1], NDArrayValue) else None
        if p == [1, 2]:
            return SparseValue(st)
        if p == [2, 1]:
            return SparseValue(st.transpose())
        return None
    if name in ("max", "min"):
        if len(args) == 1:
            ax = 1 if st.m == 1 and st.n != 1 else 0
        elif len(args) == 3 and args[1].numel() == 0:
            ax = _sum_dim(st, [args[0], args[2]])
        else:
            return None
        if ax is None or (st.m == 0 or st.n == 0):
            return None
        r = st.extreme(ax, name == "max")
        return None if r is None else SparseValue(r)
    return None


def _keep_sparse(fn, name=""):
    """Zero-preserving builtins return sparse for sparse input (MATLAB)."""

    def _wrapped(args, *, nargout=1):
        nat = native_sparse_call(name, args, nargout)
        if nat is not None:
            return (nat,)
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
    return (SparseValue(Store.zeros(m, n)),)


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
        R, C, V = [], [], []
        for c, k in enumerate(d):  # later diagonals overwrite earlier (assignment)
            i, j, b = _diag_index(int(k), m, n)
            ok = b < B.shape[0]
            R.append(i[ok]); C.append(j[ok]); V.append(B[b[ok], c])
        dt = np.result_type(B, np.float64)
        st = Store.zeros(m, n, dt)
        for r_, c_, v_ in zip(R, C, V):
            st = st.assign_linear(c_ * m + r_, v_.astype(dt), m, n) if r_.size else st
        return (SparseValue(st),)
    if len(args) in (1, 2):  # B = spdiags(A[, d]), [B, d] = spdiags(A)
        if is_sparse(args[0]):
            return _spdiags_extract(args, nargout)
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


def _spdiags_extract(args, nargout):
    st = args[0].store
    m, n = st.shape
    diag = st.cols - st.rows
    if len(args) == 2:
        d = _num("spdiags", args[1]).reshape(-1).real.astype(int)
    else:
        d = np.unique(diag).astype(int)
    out = np.zeros((min(m, n), d.size), dtype=st.dtype if st.dtype != np.bool_ else np.float64)
    for c, k in enumerate(d):
        sel = diag == k
        i, j = st.rows[sel], st.cols[sel]
        b = j if m >= n else i
        out[b, c] = st.data[sel]
    res = [NDArrayValue(out)]
    if nargout > 1:
        res.append(NDArrayValue(d.reshape(-1, 1).astype(float)))
    return tuple(res)


def _sprand(args, *, nargout=1):
    if len(args) == 1 and is_sparse(args[0]):
        st = args[0].store
        return (SparseValue(st.with_data(np.random.random_sample(st.nnz), np.float64)),)
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
    k = int(round(dens * m * n))
    if not k:
        return (SparseValue(Store.zeros(m, n)),)
    if m * n <= 10_000_000:
        pos = np.random.choice(m * n, size=k, replace=False)
    else:  # bounded memory: rejection-sample distinct positions
        pos = np.unique(np.random.randint(0, m * n, size=k, dtype=np.int64))
        while pos.size < k:
            pos = np.unique(np.concatenate([pos, np.random.randint(0, m * n, size=k - pos.size, dtype=np.int64)]))
    vals = np.random.random_sample(k)
    c, r = np.divmod(pos.astype(np.int64), m)
    return (SparseValue(Store(m, n, r, c, vals)),)


def _spfun(args, *, nargout=1):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if len(args) != 2 or not isinstance(args[0], FunctionHandleValue):
        raise _err("spfun: usage spfun(fh, S)")
    if is_sparse(args[1]):
        st = args[1].store
        rows, cols, vals = st.rows, st.cols, st.data.reshape(-1, 1)
        shape = st.shape
    else:
        A = _num("spfun", args[1])
        A = A.reshape(1, 1) if A.ndim == 0 else A
        rows, cols = np.nonzero(A.T)  # column-major order of nonzeros
        rows, cols = cols, rows
        vals = A[rows, cols].reshape(-1, 1)
        shape = A.shape
    res = args[0].call([NDArrayValue(vals.astype(np.float64) if vals.dtype == np.bool_ else vals)], nargout=1)
    if not res or not isinstance(res[0], Array) or res[0].numel() != vals.size:
        raise _err("spfun: function must return one value per nonzero element")
    rv = np.asarray(res[0].backend_buffer()).reshape(-1)
    dt = np.result_type(rv, np.float64)
    return (SparseValue(Store(shape[0], shape[1], rows, cols, rv.astype(dt), dtype=dt)),)


def _find_sparse(fn):
    """find(S) / [i,j] / [i,j,v] straight from the compressed arrays (#515)."""

    def _wrapped(args, *, nargout=1):
        if len(args) != 1 or not is_sparse(args[0]):
            return fn(args, nargout=nargout)
        st = args[0].store
        row = st.m == 1 and st.n != 1

        def col(x):
            x = np.asarray(x)
            return NDArrayValue(x.reshape(1, -1).copy() if row else x.reshape(-1, 1).copy())

        if nargout <= 1:
            return (col((st.keys + 1).astype(np.float64)),)
        out = [col((st.rows + 1).astype(np.float64)), col((st.cols + 1).astype(np.float64))]
        if nargout >= 3:
            out.append(col(st.data))
        return tuple(out)

    return _wrapped


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        sparse=_sparse, full=_full, issparse=_issparse, nnz=_nnz, nonzeros=_nonzeros,
        nzmax=_nnz, speye=_speye, spones=_spones,
        spalloc=_spalloc, spdiags=_spdiags, sprand=_sprand, spfun=_spfun,
    )
    for k in _ZERO_PRESERVING:
        if k in builtins:
            builtins[k] = _keep_sparse(builtins[k], k)
    if "find" in builtins:
        builtins["find"] = _find_sparse(builtins["find"])
