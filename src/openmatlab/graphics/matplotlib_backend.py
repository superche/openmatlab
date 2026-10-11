"""Matplotlib GraphicsBackend — Agg-friendly for CI / headless."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

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

        if not interactive:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        self._plt = plt
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
        return float(len(self._figures))

    def close(self, handle: Optional[Any] = None) -> None:
        if handle is None:
            for fig in self._figures:
                self._plt.close(fig)
            self._figures.clear()
            return
        idx = int(float(handle)) - 1
        if 0 <= idx < len(self._figures):
            self._plt.close(self._figures[idx])

    def show(self) -> None:
        # Agg: no interactive window; no-op is correct for CI
        return None

    @property
    def last_figure(self) -> Any:
        return self._figures[-1] if self._figures else None
