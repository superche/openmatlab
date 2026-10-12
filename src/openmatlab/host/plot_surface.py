"""Plot surface — host façade over GraphicsBackend."""

from __future__ import annotations

from typing import Any, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class PlotSurface(Protocol):
    def plot(self, *args: Any, **kwargs: object) -> object: ...

    def close(self, handle: Optional[object] = None) -> None: ...

    def show(self) -> None: ...

    def list_figures(self) -> List[Tuple[float, str]]: ...

    def focus(self, handle: object) -> None: ...


class StubPlotSurface:
    def __init__(self, backend: Any = None) -> None:
        self._backend = backend

    def plot(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError("PlotSurface.plot: no GraphicsBackend wired")

    def close(self, handle: Optional[object] = None) -> None:
        raise NotImplementedError("PlotSurface.close: no GraphicsBackend wired")

    def show(self) -> None:
        raise NotImplementedError("PlotSurface.show: no GraphicsBackend wired")

    def list_figures(self) -> List[Tuple[float, str]]:
        return []

    def focus(self, handle: object) -> None:
        raise NotImplementedError("PlotSurface.focus: no GraphicsBackend wired")


class HostPlotSurface:
    """Delegates to a GraphicsBackend (e.g. Matplotlib)."""

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    def plot(self, *args: Any, **kwargs: object) -> object:
        return self._backend.plot(*args, **kwargs)

    def close(self, handle: Optional[object] = None) -> None:
        self._backend.close(handle)

    def show(self) -> None:
        show = getattr(self._backend, "show", None)
        if callable(show):
            show()

    def list_figures(self) -> List[Tuple[float, str]]:
        list_fn = getattr(self._backend, "list_figures", None)
        if callable(list_fn):
            return list(list_fn())
        return []

    def focus(self, handle: object) -> None:
        focus_fn = getattr(self._backend, "focus", None)
        if not callable(focus_fn):
            raise NotImplementedError("PlotSurface.focus: backend has no focus")
        focus_fn(handle)
