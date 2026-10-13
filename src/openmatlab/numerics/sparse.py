"""MATLAB sparse attribute (Epic #487, #451).

NumPy-only design: ``SparseValue`` is an ``NDArrayValue`` (double, complex or
logical, always 2-D) that carries the sparse attribute. MATLAB-visible
behaviour (issparse, propagation rules, triplet display) matches; storage is
dense, so memory is O(m*n) (compressed storage is a filed residual).
"""

from __future__ import annotations

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


class SparseValue(NDArrayValue):
    __slots__ = ()
    issparse = True

    def __repr__(self) -> str:
        return f"SparseValue(shape={self.shape})"


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
