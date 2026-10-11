"""Matplotlib GraphicsBackend placeholder — architecture stub."""

from __future__ import annotations

from typing import Any, Optional

from openmatlab.runtime.value import Value


class MatplotlibGraphicsBackend:
    def plot(self, *args: Value, **kwargs: Any) -> Any:
        raise NotImplementedError(
            "MatplotlibGraphicsBackend.plot: architecture stub"
        )

    def close(self, handle: Optional[Any] = None) -> None:
        raise NotImplementedError(
            "MatplotlibGraphicsBackend.close: architecture stub"
        )

    def show(self) -> None:
        raise NotImplementedError(
            "MatplotlibGraphicsBackend.show: architecture stub"
        )
