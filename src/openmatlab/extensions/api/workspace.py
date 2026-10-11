"""workspace Host API — configuration read."""

from __future__ import annotations

from typing import Any, Dict, Optional

_config: Dict[str, Any] = {}
_active: Optional["WorkspaceAPI"] = None


class WorkspaceAPI:
    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}

    def set_configuration(self, section: str, value: Any) -> None:
        self._config[section] = value

    def get_configuration(self, section: str) -> Any:
        return self._config.get(section)

    def merge_contributed(self, contributed: Dict[str, Any]) -> None:
        self._config.update(contributed)


def bind(api: Optional[WorkspaceAPI]) -> None:
    global _active
    _active = api


def get_configuration(section: str) -> Any:
    if _active is not None:
        return _active.get_configuration(section)
    return _config.get(section)
