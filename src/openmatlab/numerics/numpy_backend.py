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
            out = self._num(aa.backend_buffer()) @ self._num(bb.backend_buffer())
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
                raise NumericsError(
                    "matrix power (^): exponent must be an integer for square matrices"
                )
            try:
                out = self._np.linalg.matrix_power(da, int(exp))
            except Exception as exc:  # singular / domain
                raise NumericsError(f"matrix power (^): {exc}") from exc
            return NDArrayValue(self._np.asarray(out, dtype=self._np.float64))
        raise NumericsError(
            "matrix power (^): requires scalars or square matrix ^ integer"
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
        data_a = self._np.asarray(data)
        if data_a.ndim < 2:
            data_a = data_a.reshape(data_a.shape + (1,) * (2 - data_a.ndim))
        rows_n, cols_n = int(data_a.shape[0]), int(data_a.shape[1])
        r0 = self._dim_indices_0based(indices[0], rows_n, label="index")
        c0 = self._dim_indices_0based(indices[1], cols_n, label="index")
        try:
            out = data_a[self._np.ix_(r0, c0)]
        except IndexError as exc:
            raise NumericsError(f"index: {exc}") from exc
        out = self._np.asarray(out, dtype=self._np.float64)
        # ix_ always 2-D; squeeze scalar
        if out.size == 1 and r0.size == 1 and c0.size == 1:
            out = out.reshape(1, 1)
        return NDArrayValue(out)

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
            """Remove 0-based indices; preserve vector orientation."""
            keep = np.ones(flat.size, dtype=bool)
            drop_0based = np.unique(np.asarray(drop_0based, dtype=np.int64).reshape(-1))
            if np.any(drop_0based < 0) or np.any(drop_0based >= flat.size):
                raise NumericsError("set_index: delete index out of range")
            keep[drop_0based] = False
            kept = flat[keep]
            rows, cols = (data.shape + (1, 1))[:2]
            if kept.size == 0:
                if rows == 1 and cols >= 1:
                    return NDArrayValue(kept.reshape(1, 0))
                return NDArrayValue(kept.reshape(0, 1))
            if rows == 1:
                return NDArrayValue(kept.reshape(1, -1))
            if cols == 1:
                return NDArrayValue(kept.reshape(-1, 1))
            # matrix linear delete → column (MATLAB)
            return NDArrayValue(kept.reshape(-1, 1))

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
                if need > flat.size:
                    flat = self._grow_linear_flat(data, flat, need)
                    flat[k - 1] = _apply_rhs(int(k.size))
                    rows, cols = self._grown_vector_shape(data, flat.size)
                    out = flat.reshape((rows, cols), order="F").copy()
                    return NDArrayValue(np.asarray(out, dtype=np.float64))
                flat[k - 1] = _apply_rhs(int(k.size))
            out = flat.reshape(data.shape, order="F").copy()
            return NDArrayValue(np.asarray(out, dtype=np.float64))

        if len(indices) == 2:
            rows_n, cols_n = int(data.shape[0]), int(data.shape[1])
            # logical → 1-based ints; grow only for non-logical integer OOB
            r0 = self._dim_indices_0based(
                indices[0], rows_n, label="set_index row"
            ) if self._is_logical(_as_nd(indices[0])) else None
            c0 = self._dim_indices_0based(
                indices[1], cols_n, label="set_index col"
            ) if self._is_logical(_as_nd(indices[1])) else None
            if r0 is not None:
                r = (r0 + 1).astype(self._np.int64)
            else:
                r = _as_1based_int_vec(
                    _as_nd(indices[0]).backend_buffer(), label="row subscript"
                )
            if c0 is not None:
                c = (c0 + 1).astype(self._np.int64)
            else:
                c = _as_1based_int_vec(
                    _as_nd(indices[1]).backend_buffer(), label="col subscript"
                )
            need_r = int(np.max(r))
            need_c = int(np.max(c))
            if need_r > data.shape[0] or need_c > data.shape[1]:
                grown = np.zeros((need_r, need_c), dtype=np.float64)
                grown[: data.shape[0], : data.shape[1]] = data
                data = grown
            if vbuf.size == 0:
                # A(i,:)=[] or A(:,j)=[] when one subscript is all indices
                rows_n, cols_n = data.shape[0], data.shape[1]
                if r.size == rows_n and np.array_equal(np.sort(r), np.arange(1, rows_n + 1)):
                    # deleting columns c
                    keep_c = [j for j in range(cols_n) if (j + 1) not in set(c.tolist())]
                    return NDArrayValue(data[:, keep_c].astype(np.float64))
                if c.size == cols_n and np.array_equal(np.sort(c), np.arange(1, cols_n + 1)):
                    keep_r = [i for i in range(rows_n) if (i + 1) not in set(r.tolist())]
                    return NDArrayValue(data[keep_r, :].astype(np.float64))
                raise NumericsError(
                    "A null assignment can have only one non-colon index."
                )
            n = int(r.size * c.size)
            if vbuf.size != 1:
                # MATLAB: shapes must agree once singleton dims are dropped
                lhs = [d for d in (int(r.size), int(c.size)) if d != 1]
                rhs = [int(d) for d in np.asarray(vbuf).shape if d != 1]
                if lhs != rhs:
                    rr, rc = (np.asarray(vbuf).shape + (1, 1))[:2]
                    raise NumericsError(
                        "Unable to perform assignment because the size of the left side "
                        f"is {r.size}-by-{c.size} and the size of the right side is "
                        f"{rr}-by-{rc}."
                    )
            rhs_flat = _apply_rhs(n)
            block = rhs_flat.reshape((r.size, c.size), order="F")
            try:
                data[np.ix_(r - 1, c - 1)] = block
            except IndexError as exc:
                raise NumericsError(f"set_index: {exc}") from exc
            return NDArrayValue(data)

        raise NumericsError("set_index: only 1 or 2 subscripts supported")

    def raw(self, a: Array) -> Any:
        return _as_nd(a).backend_buffer()
