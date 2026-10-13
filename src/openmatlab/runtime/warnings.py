"""Minimal MATLAB warning channel (Epic #496): warning(msg), warning('off'|'on','all'), lastwarn."""

from __future__ import annotations

import sys

_state = {"enabled": True, "last": ""}


def emit(msg: str) -> None:
    _state["last"] = msg
    if _state["enabled"]:
        print(f"Warning: {msg}", file=sys.stderr)


def set_enabled(on: bool) -> None:
    _state["enabled"] = on


def last() -> str:
    return _state["last"]


def set_last(msg: str) -> None:
    _state["last"] = msg
