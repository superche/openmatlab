"""GraphicsBackend — draw from runtime Values (vectors/matrices)."""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from openmatlab.runtime.value import Value


@runtime_checkable
class GraphicsBackend(Protocol):
    def plot(self, *args: Value, **kwargs: Any) -> Any:
        """2-D plot; return a backend figure/axes handle."""
        ...

    def close(self, handle: Optional[Any] = None) -> None:
        ...

    def show(self) -> None:
        """Flush/show interactive window if applicable."""
        ...
