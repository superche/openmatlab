"""Array-first value model.

MATLAB-like semantics treat numerics as arrays; a scalar is a 1×1 array.
Do NOT reintroduce dict[str, float] as the primary eval result type.
"""

from __future__ import annotations

from typing import Any, Protocol, Tuple, runtime_checkable


@runtime_checkable
class Value(Protocol):
    """Opaque runtime value (arrays, future char/logical/cell/handle)."""

    def matlab_class(self) -> str:
        """Public-doc style class name, e.g. 'double', 'char'."""
        ...


@runtime_checkable
class Array(Value, Protocol):
    """Numeric (or logical) N-D array — the default MATLAB-like value."""

    @property
    def shape(self) -> Tuple[int, ...]:
        ...

    @property
    def ndim(self) -> int:
        ...

    def is_scalar(self) -> bool:
        """True iff numel == 1 (scalar-as-1x1)."""
        ...

    def numel(self) -> int:
        ...

    def backend_buffer(self) -> Any:
        """Escape hatch to ArrayBackend storage (e.g. numpy.ndarray)."""
        ...


class UnimplementedValue:
    """Placeholder concrete type so imports/type checks have an anchor."""

    def matlab_class(self) -> str:
        return "unimplemented"
