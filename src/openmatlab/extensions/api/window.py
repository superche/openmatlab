"""window Host API — messages + panel registration (smoke-level)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

_messages: List[str] = []
_panels: Dict[str, Any] = {}
_active: Optional["WindowAPI"] = None


class WindowAPI:
    def __init__(self) -> None:
        self.messages: List[str] = []
        self.panels: Dict[str, Any] = {}

    def show_information_message(self, msg: str) -> None:
        text = str(msg)
        self.messages.append(text)
        print(f"[openmatlab] {text}")

    def register_panel(self, panel_id: str, factory: Callable[..., Any]) -> None:
        if not isinstance(panel_id, str) or not panel_id:
            raise ValueError("panel id must be a non-empty string")
        self.panels[panel_id] = factory

    def clear(self) -> None:
        self.messages.clear()
        self.panels.clear()


def bind(api: Optional[WindowAPI]) -> None:
    global _active
    _active = api


def show_information_message(msg: str) -> None:
    if _active is not None:
        _active.show_information_message(msg)
        return
    _messages.append(str(msg))
    print(f"[openmatlab] {msg}")


def register_panel(panel_id: str, factory: Callable[..., Any]) -> None:
    if _active is not None:
        _active.register_panel(panel_id, factory)
        return
    _panels[panel_id] = factory
