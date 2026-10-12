"""path Host API — thin wrappers over ToolboxPath."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

_active: Optional["PathAPI"] = None


class PathAPI:
    def __init__(self, toolbox_path: Any = None) -> None:
        self._path = toolbox_path

    def bind_toolbox(self, toolbox_path: Any) -> None:
        self._path = toolbox_path

    def addpath(self, entry: str | Path, *, append: bool = False) -> None:
        if self._path is None:
            raise RuntimeError("no ToolboxPath bound to path API")
        self._path.addpath(entry, append=append)

    def which(self, name: str) -> Optional[Path]:
        if self._path is None:
            raise RuntimeError("no ToolboxPath bound to path API")
        return self._path.find_mfile(name)

    def list(self) -> Sequence[Path]:
        if self._path is None:
            return ()
        return self._path.list()


def bind(api: Optional[PathAPI]) -> None:
    global _active
    _active = api


def addpath(entry: str | Path, *, append: bool = False) -> None:
    if _active is None:
        raise RuntimeError("path API not bound (no PluginHost active)")
    _active.addpath(entry, append=append)


def which(name: str) -> Optional[Path]:
    if _active is None:
        raise RuntimeError("path API not bound (no PluginHost active)")
    return _active.which(name)
