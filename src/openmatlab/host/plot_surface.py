"""Plot surface — host hook for interactive try/plot/tweak.

Delegates drawing to openmatlab.graphics.GraphicsBackend. Keeps the REPL
and future notebook/GUI free of backend details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from openmatlab.graphics.backend import GraphicsBackend
    from openmatlab.runtime.value import Value


@runtime_checkable
class PlotSurface(Protocol):
    """Workbench plotting façade."""

    def plot(self, *args: Value, **kwargs: object) -> object:
        """Create/update a 2-D line plot; returns a figure/axes handle value."""
        ...

    def close(self, handle: Optional[object] = None) -> None:
        ...


class StubPlotSurface:
    """Architecture stub — raises until a GraphicsBackend is wired."""

    def __init__(self, backend: Optional[GraphicsBackend] = None) -> None:
        self._backend = backend

    def plot(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError(
            "PlotSurface.plot: wire GraphicsBackend (architecture stage)"
        )

    def close(self, handle: Optional[object] = None) -> None:
        raise NotImplementedError(
            "PlotSurface.close: wire GraphicsBackend (architecture stage)"
        )
