"""Matplotlib GraphicsBackend — Agg-friendly for CI / headless."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from openmatlab.runtime.value import Array, Value


class GraphicsError(Exception):
    pass


def _as_1d(val: Value) -> Any:
    import numpy as np

    if not isinstance(val, Array):
        raise GraphicsError(f"plot expects Array, got {type(val)!r}")
    data = np.asarray(val.backend_buffer(), dtype=float).reshape(-1)
    return data


class MatplotlibGraphicsBackend:
    """2-D line plots via matplotlib (defaults to Agg)."""

    def __init__(self, *, interactive: bool = False) -> None:
        import matplotlib

        self._interactive = bool(interactive)
        if not self._interactive:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        self._plt = plt
        # 1-based handle N lives at index N-1; None = closed slot
        self._figures: List[Any] = []

    def plot(self, *args: Value, **kwargs: Any) -> Any:
        if not args:
            raise GraphicsError("plot requires at least one argument")
        fig, ax = self._plt.subplots()
        if len(args) == 1:
            y = _as_1d(args[0])
            ax.plot(y, **{k: v for k, v in kwargs.items() if k in ("label", "color")})
        else:
            x = _as_1d(args[0])
            y = _as_1d(args[1])
            if x.size != y.size:
                raise GraphicsError(
                    f"plot: x and y length mismatch ({x.size} vs {y.size})"
                )
            ax.plot(
                x,
                y,
                **{k: v for k, v in kwargs.items() if k in ("label", "color")},
            )
        self._figures.append(fig)
        handle = float(len(self._figures))
        try:
            fig.canvas.manager.set_window_title(f"Figure {int(handle)}")
        except Exception:
            pass
        return handle

    def close(self, handle: Optional[Any] = None) -> None:
        if handle is None:
            for fig in self._figures:
                if fig is not None:
                    self._plt.close(fig)
            self._figures.clear()
            return
        idx = int(float(handle)) - 1
        if 0 <= idx < len(self._figures) and self._figures[idx] is not None:
            self._plt.close(self._figures[idx])
            self._figures[idx] = None

    def show(self) -> None:
        """Block/show windows when interactive; no-op under Agg (CI)."""
        if self._interactive and any(f is not None for f in self._figures):
            self._plt.show()
        return None

    def list_figures(self) -> List[Tuple[float, str]]:
        """Open figures as (1-based handle, title)."""
        out: List[Tuple[float, str]] = []
        for i, fig in enumerate(self._figures):
            if fig is None:
                continue
            try:
                if not self._plt.fignum_exists(fig.number):
                    self._figures[i] = None
                    continue
            except Exception:
                pass
            handle = float(i + 1)
            title = f"Figure {int(handle)}"
            try:
                mgr = getattr(fig.canvas, "manager", None)
                if mgr is not None and hasattr(mgr, "get_window_title"):
                    t = mgr.get_window_title()
                    if t:
                        title = str(t)
            except Exception:
                pass
            out.append((handle, title))
        return out

    def focus(self, handle: Any) -> None:
        """Make figure current (and raise window when interactive)."""
        idx = int(float(handle)) - 1
        if idx < 0 or idx >= len(self._figures) or self._figures[idx] is None:
            raise GraphicsError(f"focus: no open figure {handle}")
        fig = self._figures[idx]
        self._plt.figure(fig.number)
        if self._interactive:
            try:
                mgr = getattr(fig.canvas, "manager", None)
                if mgr is not None and hasattr(mgr, "window"):
                    win = mgr.window
                    if hasattr(win, "lift"):
                        win.lift()
                    elif hasattr(win, "deiconify"):
                        win.deiconify()
            except Exception:
                pass

    @property
    def interactive(self) -> bool:
        return self._interactive

    @property
    def last_figure(self) -> Any:
        for fig in reversed(self._figures):
            if fig is not None:
                return fig
        return None
