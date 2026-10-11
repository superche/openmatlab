"""Plot surface — host façade over GraphicsBackend."""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class PlotSurface(Protocol):
    def plot(self, *args: Any, **kwargs: object) -> object: ...

    def close(self, handle: Optional[object] = None) -> None: ...


class StubPlotSurface:
    def __init__(self, backend: Any = None) -> None:
        self._backend = backend

    def plot(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError("PlotSurface.plot: no GraphicsBackend wired")

    def close(self, handle: Optional[object] = None) -> None:
        raise NotImplementedError("PlotSurface.close: no GraphicsBackend wired")


class HostPlotSurface:
    """Delegates to a GraphicsBackend (e.g. Matplotlib)."""

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    def plot(self, *args: Any, **kwargs: object) -> object:
        return self._backend.plot(*args, **kwargs)

    def close(self, handle: Optional[object] = None) -> None:
        self._backend.close(handle)
