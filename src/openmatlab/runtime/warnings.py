"""Minimal MATLAB warning channel (Epic #496, ids #498): warning(msg), warning(id, fmt, ...),
warning('off'|'on', 'all'|id), [msg, id] = lastwarn."""

from __future__ import annotations

import sys

_state = {"enabled": True, "last": "", "last_id": "", "off_ids": set()}


def emit(msg: str, ident: str = "") -> None:
    _state["last"] = msg
    _state["last_id"] = ident
    if _state["enabled"] and ident not in _state["off_ids"]:
        print(f"Warning: {msg}", file=sys.stderr)


def set_enabled(on: bool) -> None:
    _state["enabled"] = on
    if on:
        _state["off_ids"].clear()


def set_id(ident: str, on: bool) -> None:
    (_state["off_ids"].discard if on else _state["off_ids"].add)(ident)


def is_on(ident: str) -> bool:
    return _state["enabled"] and ident not in _state["off_ids"]


def last() -> str:
    return _state["last"]


def last_id() -> str:
    return _state["last_id"]


def set_last(msg: str, ident: str = "") -> None:
    _state["last"] = msg
    _state["last_id"] = ident
