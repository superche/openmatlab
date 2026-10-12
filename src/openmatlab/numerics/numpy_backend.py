"""NumPy-backed ArrayBackend — concrete numerics for OpenMATLAB."""

from __future__ import annotations

from typing import Any, Sequence, Tuple

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.value import Array


class NumericsError(Exception):
    """Numeric / shape error at the ArrayBackend seam."""


def _require_numpy():
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            'NumPy required: pip install -e ".[numpy]"'
        ) from exc
    return np


def _as_nd(a: Array) -> NDArrayValue:
    if isinstance(a, NDArrayValue):
        return a
    buf = a.backend_buffer()
    np = _require_numpy()
    if isinstance(buf, np.ndarray):
        return NDArrayValue(buf)
    raise TypeError(f"Unsupported Array type: {type(a)!r}")


class NumPyArrayBackend:
    """ArrayBackend using NumPy. Import numpy only when constructed/used."""

    def __init__(self) -> None:
        self._np = _require_numpy()

    def zeros(self, shape: Tuple[int, ...]) -> Array:
        return NDArrayValue(self._np.zeros(shape, dtype=self._np.float64))

    def ones(self, shape: Tuple[int, ...]) -> Array:
        return NDArrayValue(self._np.ones(shape, dtype=self._np.float64))

    def eye(self, n: int) -> Array:
        if n < 0:
            raise NumericsError("eye: n must be >= 0")
        return NDArrayValue(self._np.eye(n, dtype=self._np.float64))

    def from_nested(self, rows: Sequence[Sequence[float]]) -> Array:
        if not rows:
            return NDArrayValue(self._np.zeros((0, 0), dtype=self._np.float64))
        width = len(rows[0])
        for i, row in enumerate(rows):
            if len(row) != width:
                raise NumericsError(
                    f"from_nested: ragged row {i}: expected {width} cols"
                )
        return NDArrayValue(self._np.asarray(rows, dtype=self._np.float64))

    def from_scalar(self, value: float) -> Array:
        """MATLAB-like scalar as 1×1."""
        return NDArrayValue(
            self._np.asarray([[float(value)]], dtype=self._np.float64)
        )

    def matmul(self, a: Array, b: Array) -> Array:
        aa, bb = _as_nd(a), _as_nd(b)
        try:
            x, y = self._num(aa.backend_buffer()), self._num(bb.backend_buffer())
            # scalar * matrix is element-wise scaling in MATLAB
            if x.size != 1 and y.size != 1 and (x.ndim > 2 or y.ndim > 2):
                raise NumericsError(
                    "Arguments must be 2-D, or at least one argument must be scalar. "
                    "Use TIMES (.*) for elementwise multiplication."
                )
            out = x * y if (x.size == 1 or y.size == 1) else x @ y
        except ValueError as exc:
            raise NumericsError(f"matmul: {exc}") from exc
        return NDArrayValue(self._np.asarray(out, dtype=self._np.float64))

    def elem_mul(self, a: Array, b: Array) -> Array:
        return self._elem(a, b, "multiply")

    def elem_div(self, a: Array, b: Array) -> Array:
        return self._elem(a, b, "true_divide")

    def add(self, a: Array, b: Array) -> Array:
        return self._elem(a, b, "add")

    def sub(self, a: Array, b: Array) -> Array:
        return self._elem(a, b, "subtract")

    def _num(self, buf: Any) -> Any:
        """Arithmetic operand: logical promotes to double (MATLAB), never bool algebra."""
        buf = self._np.asarray(buf)
        if buf.dtype == self._np.bool_:
            return buf.astype(self._np.float64)
        return buf

    def _elem(self, a: Array, b: Array, op: str) -> Array:
        aa, bb = _as_nd(a), _as_nd(b)
        fn = getattr(self._np, op)
        try:
            out = fn(self._num(aa.backend_buffer()), self._num(bb.backend_buffer()))
        except ValueError as exc:
            raise NumericsError(f"{op}: {exc}") from exc
        out_a = self._np.asarray(out)
        if not self._np.iscomplexobj(out_a):
            out_a = out_a.astype(self._np.float64, copy=False)
        return NDArrayValue(out_a)

    def transpose(self, a: Array, *, conjugate: bool = True) -> Array:
        aa = _as_nd(a)
        data = aa.backend_buffer()
        if data.ndim > 2:
            raise NumericsError("Transpose on ND array is not defined. Use PERMUTE instead.")
        if conjugate and self._np.iscomplexobj(data):
            out = data.conj().T
        else:
            out = data.T
        return NDArrayValue(self._np.asarray(out))

    def power(self, a: Array, b: Array, *, elementwise: bool = True) -> Array:
        aa, bb = _as_nd(a), _as_nd(b)
        da = self._np.asarray(aa.backend_buffer())
        db = self._np.asarray(bb.backend_buffer())
        if not (self._np.iscomplexobj(da) or self._np.iscomplexobj(db)):
            da = da.astype(self._np.float64, copy=False)
            db = db.astype(self._np.float64, copy=False)
        if elementwise:
            out = da ** db
            return NDArrayValue(self._np.asarray(out, dtype=self._np.float64))
        # Matrix power (^): scalars or square matrix ^ integer
        if da.size == 1 and db.size == 1:
            out = float(da.reshape(-1)[0]) ** float(db.reshape(-1)[0])
            return NDArrayValue(self._np.asarray(out, dtype=self._np.float64).reshape(1, 1))
        if da.ndim == 2 and da.shape[0] == da.shape[1] and db.size == 1:
            exp = float(db.reshape(-1)[0])
            if exp != int(exp):
                return NDArrayValue(_fractional_matrix_power(self._np, da, exp))
            try:
                out = self._np.linalg.matrix_power(da, int(exp))
            except Exception as exc:  # singular / domain
                raise NumericsError(f"matrix power (^): {exc}") from exc
            return NDArrayValue(self._np.asarray(out, dtype=self._np.float64))
        if da.size == 1 and db.ndim == 2 and db.shape[0] == db.shape[1]:
            # s^A = expm(log(s) * A)  (MATLAB, s > 0)
            base = float(da.reshape(-1)[0])
            if base <= 0:
                raise NumericsError("matrix power (^): scalar^matrix needs a positive base (complex: #71)")
            return NDArrayValue(expm(self._np.log(base) * db))
        raise NumericsError(
            "matrix power (^): requires scalars, square matrix ^ scalar, or scalar ^ square matrix"
        )

    def colon(self, start: float, stop: float, step: float = 1.0) -> Array:
        if step == 0:
            raise NumericsError("colon: step must be non-zero")
        vals = self._np.arange(start, stop + (step * 0.25), step, dtype=self._np.float64)
        # inclusive stop like MATLAB when it lands on grid
        if vals.size == 0:
            return NDArrayValue(vals.reshape(1, 0))
        # trim overshoot
        if step > 0:
            vals = vals[vals <= stop + 1e-12]
        else:
            vals = vals[vals >= stop - 1e-12]
        return NDArrayValue(vals.reshape(1, -1))


    def _is_logical(self, a: Array) -> bool:
        try:
            return a.matlab_class() == "logical"
        except Exception:
            buf = _as_nd(a).backend_buffer()
            return self._np.issubdtype(buf.dtype, self._np.bool_)


    def _dim_indices_0based(self, ind: "Array", dim_size: int, *, label: str) -> Any:
        """Integer or logical subscript → 0-based index array for one dim."""
        np = self._np
        ind_a = _as_nd(ind)
        if self._is_logical(ind_a):
            m = np.asarray(ind_a.backend_buffer(), dtype=bool).reshape(-1, order="F")
            if m.size != dim_size:
                raise NumericsError(
                    f"{label}: logical mask numel ({m.size}) != dimension ({dim_size})"
                )
            return np.nonzero(m)[0].astype(np.int64)
        buf = np.asarray(ind_a.backend_buffer(), dtype=np.float64).reshape(-1)
        if buf.size == 0:
            return np.zeros(0, dtype=np.int64)
        if np.any(buf != np.floor(buf)) or np.any(buf < 1):
            raise NumericsError(f"{label}: indices must be positive integers")
        k = buf.astype(np.int64) - 1
        if np.any(k >= dim_size):
            raise NumericsError(f"{label}: index exceeds dimension ({dim_size})")
        return k

    def index(self, a: Array, indices: Sequence[Array]) -> Array:
        """1-based MATLAB-like subscript into ndarray."""
        aa = _as_nd(a)
        data = aa.backend_buffer()
        if len(indices) == 1:
            ind_a = _as_nd(indices[0])
            if self._is_logical(ind_a):
                return self._logical_index(data, ind_a.backend_buffer())
            return self._linear_index(data, ind_a.backend_buffer())
        return self._subscript_index(data, indices)

    @staticmethod
    def _collapsed_shape(shape: tuple, k: int) -> tuple:
        """MATLAB k-subscript view: pad with 1s, or fold trailing dims into the
        last subscript (A(i,j) on a 2x2x2 array addresses columns 1..4)."""
        shape = tuple(int(x) for x in shape)
        if len(shape) < k:
            return shape + (1,) * (k - len(shape))
        if len(shape) > k:
            tail = 1
            for d in shape[k - 1 :]:
                tail *= d
            return shape[: k - 1] + (tail,)
        return shape

    def _subscript_index(self, data: Any, indices: Sequence[Array]) -> Array:
        """N subscripts (N >= 2) into an N-D array (#74, #173)."""
        np = self._np
        data_a = np.asarray(data)
        k = len(indices)
        view = data_a.reshape(self._collapsed_shape(data_a.shape, k), order="F")
        idx = [
            self._dim_indices_0based(ind, view.shape[d], label="index")
            for d, ind in enumerate(indices)
        ]
        try:
            out = view[np.ix_(*idx)]
        except IndexError as exc:
            raise NumericsError(f"index: {exc}") from exc
        if data_a.dtype != np.bool_:
            out = np.asarray(out, dtype=np.float64)
        return NDArrayValue(np.array(out))

    def _linear_index(self, data: Any, ind: Any) -> Array:
        """Single subscript: column-major linear index (1-based)."""
        np = self._np
        flat_idx = np.asarray(ind, dtype=np.float64)
        if np.any(flat_idx != np.floor(flat_idx)) or np.any(flat_idx < 1):
            raise NumericsError("index: subscripts must be positive integers")
        k = flat_idx.astype(np.int64) - 1
        flat = np.asarray(data).reshape(-1, order="F")
        if np.any(k >= flat.size):
            raise NumericsError(
                f"index: linear index exceeds numel ({flat.size})"
            )
        picked = flat[k.reshape(-1)].astype(np.float64)
        if k.size == 1:
            return NDArrayValue(picked.reshape(1, 1))
        rows, cols = (np.asarray(data).shape + (1, 1))[:2]
        if np.asarray(data).ndim > 2:  # N-D source: result takes the index's shape
            rows = cols = 0
        if rows == 1:  # row-vector source keeps row orientation
            return NDArrayValue(picked.reshape(1, -1))
        if cols == 1:  # column-vector source keeps column orientation
            return NDArrayValue(picked.reshape(-1, 1))
        return NDArrayValue(picked.reshape(np.asarray(ind).shape))

    def _logical_index(self, data: Any, mask: Any) -> Array:
        """Linear logical mask (column-major), MATLAB A(L)."""
        np = self._np
        data_a = np.asarray(data)
        flat = data_a.reshape(-1, order="F")
        m = np.asarray(mask, dtype=bool).reshape(-1, order="F")
        if m.size != flat.size:
            raise NumericsError(
                f"index: logical mask numel ({m.size}) != array numel ({flat.size})"
            )
        picked = flat[m].astype(np.float64)
        rows, cols = (data_a.shape + (1, 1))[:2]
        if data_a.ndim > 2:  # N-D mask/source → column (#322)
            rows = cols = 0
        if picked.size == 0:
            if rows == 1:
                return NDArrayValue(picked.reshape(1, 0))
            return NDArrayValue(picked.reshape(0, 1))
        if rows == 1:
            return NDArrayValue(picked.reshape(1, -1))
        if cols == 1:
            return NDArrayValue(picked.reshape(-1, 1))
        return NDArrayValue(picked.reshape(-1, 1))


    def _grown_vector_shape(self, data: Any, new_numel: int) -> tuple:
        """Orientation after linear grow: row stays row, else column."""
        rows, cols = (self._np.asarray(data).shape + (1, 1))[:2]
        if rows == 1:
            return (1, int(new_numel))
        return (int(new_numel), 1)

    def _grow_linear_flat(self, data: Any, flat: Any, need: int) -> Any:
        np = self._np
        grown = np.zeros(need, dtype=np.float64)
        grown[: flat.size] = flat
        return grown

    def set_index(self, a: Array, indices: Sequence[Array], value: Array) -> Array:
        """1-based copy-on-write set; scalar or matching-numel RHS; range LHS ok."""
        aa = _as_nd(a)
        vv = _as_nd(value)
        vbuf = self._np.asarray(vv.backend_buffer(), dtype=self._np.float64)
        data = self._np.asarray(aa.backend_buffer(), dtype=self._np.float64).copy()
        np = self._np

        def _as_1based_int_vec(buf: Any, *, label: str) -> Any:
            flat = np.asarray(buf, dtype=np.float64).reshape(-1)
            if flat.size == 0:
                raise NumericsError(f"set_index: empty {label}")
            if np.any(flat != np.floor(flat)) or np.any(flat < 1):
                raise NumericsError("set_index: indices must be positive integers")
            return flat.astype(np.int64)

        def _apply_rhs(n: int) -> Any:
            if vbuf.size == 0:
                raise NumericsError("set_index: internal empty RHS")
            if vbuf.size == 1:
                return np.full(n, float(vbuf.reshape(-1)[0]), dtype=np.float64)
            if vbuf.size != n:
                raise NumericsError(
                    f"set_index: RHS numel ({vbuf.size}) != LHS numel ({n})"
                )
            return np.asarray(vbuf, dtype=np.float64).reshape(-1, order="F")

        def _delete_linear(flat: Any, drop_0based: Any) -> Array:
            """Remove 0-based indices (MATLAB): row/column vectors keep orientation;
            a matrix is reshaped to a 1-by-N row (public MATLAB indexing docs)."""
            keep = np.ones(flat.size, dtype=bool)
            drop_0based = np.unique(np.asarray(drop_0based, dtype=np.int64).reshape(-1))
            if np.any(drop_0based < 0) or np.any(drop_0based >= flat.size):
                raise NumericsError("set_index: delete index out of range")
            keep[drop_0based] = False
            kept = flat[keep]
            rows, cols = (data.shape + (1, 1))[:2]
            if cols == 1 and rows != 1:
                return NDArrayValue(kept.reshape(-1, 1))  # column (incl. 0x1)
            return NDArrayValue(kept.reshape(1, -1))  # row vector or matrix → 1xN

        if len(indices) == 1:
            ind_a = _as_nd(indices[0])
            flat = np.asarray(data, order="F").reshape(-1, order="F").copy()
            if vbuf.size == 0:
                # A(i)=[] delete
                if self._is_logical(ind_a):
                    m = np.asarray(ind_a.backend_buffer(), dtype=bool).reshape(
                        -1, order="F"
                    )
                    if m.size != flat.size:
                        raise NumericsError(
                            f"set_index: logical mask numel ({m.size}) != array numel ({flat.size})"
                        )
                    drop = np.nonzero(m)[0]
                else:
                    k = _as_1based_int_vec(
                        ind_a.backend_buffer(), label="linear index"
                    )
                    if np.any(k > flat.size):
                        raise NumericsError(
                            f"set_index: linear index exceeds numel ({flat.size})"
                        )
                    drop = k - 1
                return _delete_linear(flat, drop)
            if self._is_logical(ind_a):
                m = np.asarray(ind_a.backend_buffer(), dtype=bool).reshape(-1, order="F")
                if m.size != flat.size:
                    raise NumericsError(
                        f"set_index: logical mask numel ({m.size}) != array numel ({flat.size})"
                    )
                nsel = int(m.sum())
                flat[m] = _apply_rhs(nsel)
            else:
                k = _as_1based_int_vec(
                    ind_a.backend_buffer(), label="linear index"
                )
                need = int(np.max(k))
                if need > flat.size and data.ndim > 2:
                    raise NumericsError("Attempt to grow array along ambiguous dimension.")
                if need > flat.size:
                    flat = self._grow_linear_flat(data, flat, need)
                    flat[k - 1] = _apply_rhs(int(k.size))
                    rows, cols = self._grown_vector_shape(data, flat.size)
                    out = flat.reshape((rows, cols), order="F").copy()
                    return NDArrayValue(np.asarray(out, dtype=np.float64))
                flat[k - 1] = _apply_rhs(int(k.size))
            out = flat.reshape(data.shape, order="F").copy()
            return NDArrayValue(np.asarray(out, dtype=np.float64))

        return self._set_subscripts(data, indices, vbuf, _as_1based_int_vec, _apply_rhs)

    def _set_subscripts(self, data, indices, vbuf, _as_1based_int_vec, _apply_rhs) -> Array:
        """A(i,j,...)=v for N >= 2 subscripts: grow with zero fill (#259),
        deletion along one non-colon subscript, MATLAB size agreement."""
        np = self._np
        k = len(indices)
        orig_shape = tuple(int(x) for x in data.shape)
        view_shape = self._collapsed_shape(orig_shape, k)
        folded = len(orig_shape) > k
        view = data.reshape(view_shape, order="F")
        subs = []
        for d, ind in enumerate(indices):
            ind_a = _as_nd(ind)
            if self._is_logical(ind_a):
                subs.append(
                    self._dim_indices_0based(ind_a, view_shape[d], label="set_index") + 1
                )
            else:
                subs.append(_as_1based_int_vec(ind_a.backend_buffer(), label="subscript"))
        need = [max(view_shape[d], int(np.max(s_))) for d, s_ in enumerate(subs)]
        if vbuf.size == 0 and tuple(need) != view_shape:
            raise NumericsError("Matrix index is out of range for deletion.")
        if tuple(need) != view_shape:
            if folded:
                raise NumericsError(
                    "Attempt to grow array along ambiguous dimension."
                )
            grown = np.zeros(need, dtype=view.dtype)
            grown[tuple(slice(0, n) for n in view_shape)] = view
            view = grown
            view_shape = tuple(need)
        if vbuf.size == 0:
            full = [
                s_.size == view_shape[d]
                and np.array_equal(np.sort(s_), np.arange(1, view_shape[d] + 1))
                for d, s_ in enumerate(subs)
            ]
            partial = [d for d, f in enumerate(full) if not f]
            if len(partial) > 1:
                raise NumericsError("A null assignment can have only one non-colon index.")
            if not partial:
                # every subscript covers its dim: empty along the last (A(:,:)=[] → Rx0)
                d = k - 1
            else:
                d = partial[0]
            out = np.delete(view, np.unique(subs[d] - 1), axis=d)
            if folded and d < k - 1:
                out = out.reshape(out.shape[: k - 1] + orig_shape[k - 1 :], order="F")
            return NDArrayValue(np.asarray(out, dtype=np.float64))
        lhs_dims = [int(s_.size) for s_ in subs]
        n = int(np.prod(lhs_dims))
        if vbuf.size != 1:
            lhs = [d for d in lhs_dims if d != 1]
            rhs = [int(d) for d in np.asarray(vbuf).shape if d != 1]
            if lhs != rhs:
                rshape = np.asarray(vbuf).shape + (1, 1)
                rdims = list(rshape[: max(2, np.asarray(vbuf).ndim)])
                raise NumericsError(
                    "Unable to perform assignment because the size of the left side "
                    f"is {'-by-'.join(map(str, lhs_dims))} and the size of the right side is "
                    f"{'-by-'.join(map(str, rdims))}."
                )
        block = _apply_rhs(n).reshape(lhs_dims, order="F")
        if view.dtype != np.float64:
            view = view.astype(np.float64)
        else:
            view = view.copy()
        view[np.ix_(*[s_ - 1 for s_ in subs])] = block
        if folded:
            view = view.reshape(orig_shape, order="F")
        return NDArrayValue(view)

    def raw(self, a: Array) -> Any:
        return _as_nd(a).backend_buffer()


def expm(m):
    """Matrix exponential: scaling and squaring with a Taylor series (no SciPy)."""
    import numpy as np

    m = np.asarray(m, dtype=np.float64)
    norm = float(np.linalg.norm(m, 1))
    s = max(0, int(np.ceil(np.log2(norm))) + 1) if norm > 0.5 else 0
    a = m / (2.0 ** s)
    term = np.eye(a.shape[0])
    out = term.copy()
    for k in range(1, 30):
        term = term @ a / k
        out = out + term
        if np.linalg.norm(term, 1) < 1e-17 * np.linalg.norm(out, 1):
            break
    for _ in range(s):
        out = out @ out
    return out


def _fractional_matrix_power(np, a, p):
    """A^p for non-integer p via eigendecomposition; real results only (complex: #71)."""
    w, v = np.linalg.eig(a)
    if np.linalg.cond(v) > 1e12:
        raise NumericsError("matrix power (^): matrix is not diagonalizable")
    out = v @ np.diag(np.power(w.astype(complex), p)) @ np.linalg.inv(v)
    if np.max(np.abs(out.imag)) > 1e-10 * max(1.0, np.max(np.abs(out.real))):
        raise NumericsError("matrix power (^): result is complex (complex numbers: #71)")
    return np.asarray(out.real, dtype=np.float64)

