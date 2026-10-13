"""MATLAB sparse attribute (Epic #487, #451).

NumPy-only design: ``SparseValue`` is an ``NDArrayValue`` (double, complex or
logical, always 2-D) that carries the sparse attribute. Since Epic #520 its
storage is compressed (``sparse_store.Store``, CSC order, O(nnz) memory).
``backend_buffer()`` still works for every legacy consumer: it materialises a
dense copy on demand and bumps ``DENSIFY_COUNT`` so tests can prove the native
paths never densify.
"""

from __future__ import annotations

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


from openmatlab.numerics.sparse_store import Store

DENSIFY_COUNT = [0]


class SparseValue(NDArrayValue):
    __slots__ = ("store",)
    issparse = True

    def __init__(self, data) -> None:
        if isinstance(data, Store):
            self.store = data
        else:
            self.store = Store.from_dense(np.asarray(data))
        self._data = None

    def matlab_class(self) -> str:
        return "logical" if self.store.dtype == np.bool_ else "double"

    @property
    def shape(self):
        return self.store.shape

    @property
    def ndim(self) -> int:
        return 2

    def numel(self) -> int:
        return self.store.m * self.store.n

    def backend_buffer(self) -> np.ndarray:
        if self._data is None:
            DENSIFY_COUNT[0] += 1
            self._data = self.store.to_dense()
        return self._data

    def __repr__(self) -> str:
        return f"SparseValue(shape={self.shape}, nnz={self.store.nnz})"


def from_store(st: Store) -> SparseValue:
    return SparseValue(st)


def is_sparse(v) -> bool:
    return bool(getattr(v, "issparse", False))


def to_sparse(buf) -> NDArrayValue:
    """Sparse value over ``buf``; N-D or integer data stays full (MATLAB has neither)."""
    b = np.asarray(buf)
    b = b.reshape(1, 1) if b.ndim == 0 else (b.reshape(1, -1) if b.ndim == 1 else b)
    if b.ndim != 2 or not (b.dtype == np.bool_ or b.dtype in (np.float64, np.complex128)):
        return NDArrayValue(b)
    return SparseValue(b)


def _buf(v):
    return np.asarray(v.backend_buffer()) if hasattr(v, "backend_buffer") else None


def _scalar(v) -> bool:
    b = _buf(v)
    return b is not None and b.size == 1


def sparse_result(kind: str, out, a=None, b=None, op: str = ""):
    """Apply MATLAB's sparsity rules to a backend result."""
    sa, sb = is_sparse(a), is_sparse(b)
    if not (sa or sb):
        return out
    if kind == "matmul":
        keep = (sa and sb) or (sa and _scalar(b)) or (sb and _scalar(a))
    elif kind == "elem":
        if op in ("add", "subtract"):
            keep = sa and sb
        elif op == "multiply":
            keep = True
        else:  # true_divide: S./X stays sparse, X./S is full
            keep = sa
    elif kind == "power":
        p = _buf(b)
        keep = sa and p is not None and p.size == 1 and not np.iscomplexobj(p) and float(p.reshape(-1)[0]) > 0
    else:  # transpose, index, set_index, concat, relational, unary
        keep = True
    return to_sparse(out.backend_buffer()) if keep else NDArrayValue(np.asarray(out.backend_buffer()))


def concat_native(rows):
    """Compressed [A B; C D] when a sparse block is involved and dims agree; else None."""
    from openmatlab.numerics.sparse_store import concat

    if not any(is_sparse(v) for r in rows for v in r):
        return None
    blocks = []
    for r in rows:
        row = []
        for v in r:
            if is_sparse(v):
                st = v.store
            elif type(v) is NDArrayValue:
                b = v.backend_buffer()
                if b.ndim > 2 or b.dtype not in (np.float64, np.complex128, np.bool_):
                    return None
                st = Store.from_dense(b)
            else:
                return None
            if st.shape != (0, 0):
                row.append(st)
        if row:
            if len({b.m for b in row}) != 1:
                return None
            blocks.append(row)
    if not blocks:
        return None
    if len({sum(b.n for b in row) for row in blocks}) != 1:
        return None
    return SparseValue(concat(blocks))


# --- native kernels behind the backend ops (#516, #517) -------------------------

def _plain(v):
    """Dense double/complex/logical buffer of a non-sparse NDArrayValue, else None."""
    if is_sparse(v) or type(v) is not NDArrayValue:
        return None
    b = v.backend_buffer()
    if b.dtype not in (np.float64, np.complex128, np.bool_) or b.ndim > 2:
        return None
    return b.reshape(1, 1) if b.ndim == 0 else (b.reshape(1, -1) if b.ndim == 1 else b)


def _err(msg):
    from openmatlab.numerics.numpy_backend import NumericsError

    return NumericsError(msg)


def _matmul(a, b):
    sa, sb = is_sparse(a), is_sparse(b)
    if sa and sb:
        if a.store.n != b.store.m:
            return None
        if a.store.shape == (1, 1) or b.store.shape == (1, 1):
            return None
        return SparseValue(a.store.matmul(b.store))
    s, d = (a, b) if sa else (b, a)
    if s.store.shape == (1, 1):
        return None
    bd = _plain(d)
    if bd is None:
        return None
    if bd.size == 1:
        r = s.store.scale(bd.reshape(-1)[0])
        return None if r is None else SparseValue(r)
    out = s.store.matvec(bd) if sa else s.store.rmatvec(bd)
    return None if out is None else NDArrayValue(out)


def _elem(a, b, op):
    sa, sb = is_sparse(a), is_sparse(b)
    if sa and sb:
        if a.store.shape != b.store.shape or a.store.shape == (1, 1):
            return None
        if op == "add":
            return SparseValue(a.store.add(b.store))
        if op == "subtract":
            return SparseValue(a.store.add(b.store, -1.0))
        if op == "multiply":
            return SparseValue(a.store.emul(b.store))
        return None
    s, d = (a, b) if sa else (b, a)
    if s.store.shape == (1, 1):
        return None
    bd = _plain(d)
    if bd is None:
        return None
    if op == "multiply":
        r = s.store.scale(bd.reshape(-1)[0]) if bd.size == 1 else s.store.emul_dense(bd)
    elif op == "true_divide" and sa:
        r = s.store.ediv_dense(bd)
    else:
        return None
    return None if r is None else SparseValue(r)


def _power(a, b, elementwise):
    if not elementwise or not is_sparse(a) or is_sparse(b):
        return None
    p = _plain(b)
    if p is None or p.size != 1 or p.dtype == np.complex128:
        return None
    p = float(p.reshape(-1)[0])
    st = a.store
    if not (np.isfinite(p) and p > 0):
        return None
    d = st.data.astype(np.float64) if st.dtype == np.bool_ else st.data
    if p != np.floor(p) and d.dtype != np.complex128 and np.any(d < 0):
        return None
    r = st.map(lambda x: np.power(x, p))
    return None if r is None else SparseValue(r)


def _index_vec(ind, size, *, label, pos=0, allow_grow=False):
    """0-based subscript vector for one dimension (mirrors the dense messages)."""
    if is_sparse(ind):
        ind = NDArrayValue(ind.store.to_dense())
    b = np.asarray(ind.backend_buffer())
    if b.dtype == np.bool_:
        m = b.reshape(-1, order="F")
        if m.size != size and not (allow_grow and m.size >= size):
            raise _err(f"{label}: logical mask numel ({m.size}) != dimension ({size})")
        return np.nonzero(m)[0].astype(np.int64)
    if b.dtype == np.complex128 or b.dtype == object:
        return None
    f = b.astype(np.float64).reshape(-1)
    if f.size == 0:
        return np.zeros(0, dtype=np.int64)
    if np.any(f != np.floor(f)) or np.any(f < 1):
        if allow_grow:
            raise _err("set_index: indices must be positive integers")
        raise _err(f"{label}: indices must be positive integers")
    k = f.astype(np.int64) - 1
    if not allow_grow and np.any(k >= size):
        if pos:
            raise _err(f"Index in position {pos} exceeds array bounds (must not exceed {size}).")
        raise _err(f"{label}: index exceeds dimension ({size})")
    return k


def _index(a, indices):
    st = a.store
    m, n = st.shape
    if len(indices) == 1:
        ind = indices[0]
        b = None if is_sparse(ind) else np.asarray(ind.backend_buffer())
        if is_sparse(ind) or b.dtype == np.bool_:
            if is_sparse(ind):
                if ind.store.dtype != np.bool_:
                    return None
                if ind.numel() != m * n:
                    raise _err(f"index: logical mask numel ({ind.numel()}) != array numel ({m * n})")
                k = ind.store.keys
            else:
                mask = b.reshape(-1, order="F")
                if mask.size != m * n:
                    raise _err(f"index: logical mask numel ({mask.size}) != array numel ({m * n})")
                k = np.nonzero(mask)[0]
            shape = (1, k.size) if m == 1 else (k.size, 1)
            return SparseValue(st.take_linear(k, *shape))
        if b.ndim > 2 or b.dtype == np.complex128:
            return None
        f = b.astype(np.float64)
        if np.any(f != np.floor(f)) or np.any(f < 1):
            raise _err("index: subscripts must be positive integers")
        k = f.astype(np.int64) - 1
        if np.any(k >= m * n):
            raise _err(f"Index exceeds the number of array elements. Index must not exceed {m * n}.")
        if k.size == 1:
            shape = (1, 1)
        elif m == 1:
            shape = (1, k.size)
        elif n == 1:
            shape = (k.size, 1)
        else:
            shape = b.shape if b.ndim == 2 else (1, k.size)
        kk = k.reshape(-1, order="F")
        # take_linear wants output positions in column-major order of the result
        return SparseValue(_take_positions(st, kk, shape))
    if len(indices) != 2:
        return None
    I = _index_vec(indices[0], m, label="index", pos=1)
    J = _index_vec(indices[1], n, label="index", pos=2)
    if I is None or J is None:
        return None
    return SparseValue(st.submatrix(I, J))


def _take_positions(st, k, shape):
    """Result of `shape` whose p-th element (column-major) is st at linear k[p]."""
    from openmatlab.numerics.sparse_store import Store

    vals = st.get_linear(k)
    p = np.nonzero(vals != 0)[0]
    r, c = (p % shape[0], p // shape[0]) if shape[0] else (p, p)
    return Store(shape[0], shape[1], r, c, vals[p], canonical=True, dtype=st.dtype)


def _rhs(value, store_dtype):
    if is_sparse(value):
        v = value.store.to_dense()
    else:
        v = _plain(value)
        if v is None:
            return None
    if (store_dtype == np.bool_) != (v.dtype == np.bool_):
        return None  # class-changing assignment: dense rules decide
    return v


def _set_index(a, indices, value):
    st = a.store
    m, n = st.shape
    v = _rhs(value, st.dtype)
    if v is None:
        return None
    if v.size == 0:
        return _delete(st, indices)
    if len(indices) == 1:
        ind = indices[0]
        if is_sparse(ind):
            return None
        b = np.asarray(ind.backend_buffer())
        if b.dtype == np.bool_:
            mask = b.reshape(-1, order="F")
            if mask.size != m * n:
                raise _err(f"set_index: logical mask numel ({mask.size}) != array numel ({m * n})")
            k = np.nonzero(mask)[0]
        else:
            k = _index_vec(ind, m * n, label="set_index", allow_grow=True)
            if k is None or k.size == 0:
                return None
        if v.size not in (1, k.size):
            raise _err(f"set_index: RHS numel ({v.size}) != LHS numel ({k.size})")
        need = int(k.max()) + 1 if k.size else 0
        mm, nn = m, n
        if need > m * n:
            mm, nn = (1, need) if (m == 1 or (m == 0 and n == 0)) else (need, 1)
            base = st.reshape(mm, nn) if m * n else st.reshape(mm, nn)
        else:
            base = st
        return SparseValue(base.assign_linear(k, v.reshape(-1, order="F"), mm, nn))
    if len(indices) != 2:
        return None
    I = _index_vec(indices[0], m, label="set_index", allow_grow=True)
    J = _index_vec(indices[1], n, label="set_index", allow_grow=True)
    if I is None or J is None or I.size == 0 or J.size == 0:
        return None
    lhs_dims = [int(I.size), int(J.size)]
    if v.size != 1:
        if [d for d in lhs_dims if d != 1] != [d for d in v.shape if d != 1]:
            raise _err(
                "Unable to perform assignment because the size of the left side "
                f"is {lhs_dims[0]}-by-{lhs_dims[1]} and the size of the right side is "
                f"{v.shape[0]}-by-{v.shape[1]}."
            )
    mm, nn = max(m, int(I.max()) + 1), max(n, int(J.max()) + 1)
    vals = v.reshape(-1, order="F").reshape(lhs_dims, order="F") if v.size != 1 else v
    return SparseValue(st.assign_block(I, J, vals, mm, nn))


def _delete(st, indices):
    from openmatlab.numerics.sparse_store import Store

    m, n = st.shape
    if len(indices) == 1:
        ind = indices[0]
        if is_sparse(ind):
            return None
        b = np.asarray(ind.backend_buffer())
        if b.dtype == np.bool_:
            mask = b.reshape(-1, order="F")
            if mask.size != m * n:
                raise _err(f"set_index: logical mask numel ({mask.size}) != array numel ({m * n})")
            drop = np.nonzero(mask)[0]
        else:
            drop = _index_vec(ind, m * n, label="set_index", allow_grow=True)
            if drop is None or drop.size == 0:
                return None
            if np.any(drop >= m * n):
                raise _err(f"set_index: linear index exceeds numel ({m * n})")
        drop = np.unique(drop)
        keys = st.keys
        keep = ~np.isin(keys, drop)
        newk = keys[keep] - np.searchsorted(drop, keys[keep])
        total = m * n - drop.size
        mm, nn = (total, 1) if (n == 1 and m != 1) else (1, total)
        r, c = (newk % mm, newk // mm) if mm else (newk, newk)
        return SparseValue(Store(mm, nn, r, c, st.data[keep], canonical=True, dtype=st.dtype))
    if len(indices) != 2:
        return None
    I = _index_vec(indices[0], m, label="set_index", allow_grow=True)
    J = _index_vec(indices[1], n, label="set_index", allow_grow=True)
    if I is None or J is None or I.size == 0 or J.size == 0:
        return None
    if int(I.max()) >= m or int(J.max()) >= n:
        raise _err("Matrix index is out of range for deletion.")
    fullI = np.unique(I).size == m
    fullJ = np.unique(J).size == n
    if not fullI and not fullJ:
        raise _err("A null assignment can have only one non-colon index.")
    if fullI and fullJ:
        return SparseValue(Store.zeros(m, 0, st.dtype))
    if fullI:
        return SparseValue(st.delete_cols(np.unique(J)))
    return SparseValue(st.delete_rows(np.unique(I)))


def native_op(name, a, args, kw):
    """Compressed-storage result for a backend op, or None to take the dense path."""
    try:
        if name == "transpose":
            if not is_sparse(a):
                return None
            return SparseValue(a.store.transpose(conj=kw.get("conjugate", True)))
        if name == "matmul":
            return _matmul(a, args[0]) if (is_sparse(a) or is_sparse(args[0])) else None
        if name == "_elem":
            return _elem(a, args[0], args[1]) if (is_sparse(a) or is_sparse(args[0])) else None
        if name == "power":
            return _power(a, args[0], kw.get("elementwise", True))
        if name == "index":
            return _index(a, list(args[0])) if is_sparse(a) else None
        if name == "set_index":
            return _set_index(a, list(args[0]), args[1]) if is_sparse(a) else None
    except (TypeError, AttributeError):
        return None
    return None
