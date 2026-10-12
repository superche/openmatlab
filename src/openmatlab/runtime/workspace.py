"""Workspace — base workspace + nested function frames."""

from __future__ import annotations

from typing import Dict, Iterator, List, Optional

from openmatlab.runtime.value import Value


class Workspace:
    """Name → Value scopes.

    `base` is the interactive / script workspace. `push`/`pop` model
    function call frames (needed before toolboxes and user functions).
    """

    def __init__(self) -> None:
        self._frames: List[Dict[str, Value]] = [{}]

    @property
    def base(self) -> Dict[str, Value]:
        return self._frames[0]

    def push(self) -> None:
        self._frames.append({})

    def pop(self) -> None:
        if len(self._frames) <= 1:
            raise RuntimeError("Cannot pop base workspace")
        self._frames.pop()

    def get(self, name: str) -> Value:
        for frame in reversed(self._frames):
            if name in frame:
                return frame[name]
        raise KeyError(name)

    def __contains__(self, name: object) -> bool:
        return any(name in frame for frame in self._frames)

    def set(self, name: str, value: Value) -> None:
        self._frames[-1][name] = value

    def clear(self, *names: str) -> None:
        if not names:
            self._frames[-1].clear()
            return
        for n in names:
            self._frames[-1].pop(n, None)

    def names(self) -> Iterator[str]:
        seen: set[str] = set()
        for frame in reversed(self._frames):
            for n in frame:
                if n not in seen:
                    seen.add(n)
                    yield n

    def depth(self) -> int:
        return len(self._frames)
