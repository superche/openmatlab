"""commands Host API — register / execute."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

# Module-level fallback used when no PluginHost is bound (tests / import smoke).
_FALLBACK_HANDLERS: Dict[str, Callable[..., Any]] = {}
_active: Optional["CommandsAPI"] = None


class CommandsAPI:
    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}

    def register_command(
        self, command_id: str, callback: Callable[..., Any], **meta: Any
    ) -> None:
        if not isinstance(command_id, str) or not command_id:
            raise ValueError("command id must be a non-empty string")
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._handlers[command_id] = callback
        if meta:
            self._meta[command_id] = dict(meta)

    def execute_command(self, command_id: str, *args: Any, **kwargs: Any) -> Any:
        handler = self._handlers.get(command_id)
        if handler is None:
            raise KeyError(f"unknown command: {command_id}")
        return handler(*args, **kwargs)

    def has(self, command_id: str) -> bool:
        return command_id in self._handlers

    def list_ids(self) -> list[str]:
        return sorted(self._handlers)

    def clear_plugin(self, _plugin_id: str) -> None:
        # Handlers are tracked on PluginHost; this clears nothing by id alone.
        pass

    def unregister(self, command_id: str) -> None:
        self._handlers.pop(command_id, None)
        self._meta.pop(command_id, None)


def bind(api: Optional[CommandsAPI]) -> None:
    global _active
    _active = api


def register_command(command_id: str, callback: Callable[..., Any], **meta: Any) -> None:
    if _active is not None:
        _active.register_command(command_id, callback, **meta)
        return
    _FALLBACK_HANDLERS[command_id] = callback


def execute_command(command_id: str, *args: Any, **kwargs: Any) -> Any:
    if _active is not None:
        return _active.execute_command(command_id, *args, **kwargs)
    if command_id not in _FALLBACK_HANDLERS:
        raise KeyError(f"unknown command: {command_id}")
    return _FALLBACK_HANDLERS[command_id](*args, **kwargs)
