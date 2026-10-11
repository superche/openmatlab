"""ArrayBackend — numeric storage and ops behind runtime.Array.

Clean-room: implementing this with NumPy/SciPy is fine and is NOT reverse
engineering MATLAB. The language/runtime must not depend on MATLAB binaries.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence, Tuple, runtime_checkable

from openmatlab.runtime.value import Array


@runtime_checkable
class ArrayBackend(Protocol):
    """Create arrays and perform matrix / element-wise / linalg ops."""

    def zeros(self, shape: Tuple[int, ...]) -> Array:
        ...

    def ones(self, shape: Tuple[int, ...]) -> Array:
        ...

    def eye(self, n: int) -> Array:
        ...

    def from_nested(self, rows: Sequence[Sequence[float]]) -> Array:
        """Build from literal row data (parser MatrixLiteral)."""
        ...

    def matmul(self, a: Array, b: Array) -> Array:
        ...

    def elem_mul(self, a: Array, b: Array) -> Array:
        ...

    def elem_div(self, a: Array, b: Array) -> Array:
        ...

    def add(self, a: Array, b: Array) -> Array:
        ...

    def sub(self, a: Array, b: Array) -> Array:
        ...

    def transpose(self, a: Array, *, conjugate: bool = True) -> Array:
        ...

    def raw(self, a: Array) -> Any:
        """Backend buffer (e.g. numpy.ndarray)."""
        ...
