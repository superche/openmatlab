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

    def raw(self, a: Array) -> Any:
        return _as_nd(a).backend_buffer()
