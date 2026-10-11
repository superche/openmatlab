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
            out = aa.backend_buffer() @ bb.backend_buffer()
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

    def _elem(self, a: Array, b: Array, op: str) -> Array:
        aa, bb = _as_nd(a), _as_nd(b)
        fn = getattr(self._np, op)
        try:
            out = fn(aa.backend_buffer(), bb.backend_buffer())
        except ValueError as exc:
            raise NumericsError(f"{op}: {exc}") from exc
        return NDArrayValue(self._np.asarray(out, dtype=self._np.float64))

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
        if elementwise:
            out = aa.backend_buffer() ** bb.backend_buffer()
        else:
            raise NumericsError("matrix power (^) not implemented yet")
        return NDArrayValue(self._np.asarray(out, dtype=self._np.float64))

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

    def index(self, a: Array, indices: Sequence[Array]) -> Array:
        """1-based MATLAB-like subscript into ndarray."""
        aa = _as_nd(a)
        data = aa.backend_buffer()
        if len(indices) == 1:
            return self._linear_index(data, _as_nd(indices[0]).backend_buffer())
        py_idx = []
        for ind in indices:
            buf = _as_nd(ind).backend_buffer()
            if buf.size == 1:
                i = int(buf.reshape(-1)[0])
                if i < 1:
                    raise NumericsError(f"index: 1-based index out of range: {i}")
                py_idx.append(i - 1)
            else:
                flat = buf.astype(self._np.int64).reshape(-1)
                if self._np.any(flat < 1):
                    raise NumericsError("index: indices must be >= 1")
                py_idx.append(flat - 1)
        try:
            out = data[tuple(py_idx)]
        except IndexError as exc:
            raise NumericsError(f"index: {exc}") from exc
        out = self._np.asarray(out, dtype=self._np.float64)
        if out.ndim == 0:
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


    def set_index(self, a: Array, indices: Sequence[Array], value: Array) -> Array:
        """1-based copy-on-write set of a single element (scalar value)."""
        aa = _as_nd(a)
        vv = _as_nd(value)
        vbuf = vv.backend_buffer()
        if vbuf.size != 1:
            raise NumericsError("set_index: RHS must be scalar in this MVP")
        scalar = float(vbuf.reshape(-1)[0])
        data = aa.backend_buffer().copy()
        if len(indices) == 1:
            # linear column-major
            ind = _as_nd(indices[0]).backend_buffer()
            if ind.size != 1:
                raise NumericsError("set_index: linear index must be scalar")
            k = int(ind.reshape(-1)[0])
            if k != float(ind.reshape(-1)[0]) or k < 1:
                raise NumericsError("set_index: indices must be positive integers")
            flat = self._np.asarray(data, order="F").reshape(-1, order="F").copy()
            if k > flat.size:
                raise NumericsError(
                    f"set_index: linear index {k} exceeds numel ({flat.size})"
                )
            flat[k - 1] = scalar
            out = flat.reshape(data.shape, order="F").copy()
            return NDArrayValue(self._np.asarray(out, dtype=self._np.float64))
        if len(indices) == 2:
            py_idx = []
            for ind in indices:
                buf = _as_nd(ind).backend_buffer()
                if buf.size != 1:
                    raise NumericsError("set_index: subscripts must be scalar")
                i = int(buf.reshape(-1)[0])
                if i != float(buf.reshape(-1)[0]) or i < 1:
                    raise NumericsError("set_index: indices must be positive integers")
                py_idx.append(i - 1)
            try:
                data[tuple(py_idx)] = scalar
            except IndexError as exc:
                raise NumericsError(f"set_index: {exc}") from exc
            return NDArrayValue(data)
        raise NumericsError("set_index: only 1 or 2 subscripts supported")

    def raw(self, a: Array) -> Any:
        return _as_nd(a).backend_buffer()
