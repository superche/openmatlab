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
        # name -> shared store for global/persistent bindings, per frame (#531)
        self._refs: List[Dict[str, Dict[str, Value]]] = [{}]

    def bind_ref(self, name: str, store: Dict[str, Value], default: Value) -> None:
        """Make ``name`` in the current frame an alias of ``store[name]``."""
        store.setdefault(name, default)
        self._frames[-1].pop(name, None)
        self._refs[-1][name] = store

    @property
    def base(self) -> Dict[str, Value]:
        return self._frames[0]

    def push(self) -> None:
        self._frames.append({})
        self._refs.append({})

    def pop(self) -> None:
        if len(self._frames) <= 1:
            raise RuntimeError("Cannot pop base workspace")
        self._frames.pop()
        self._refs.pop()

    def get(self, name: str) -> Value:
        ref = self._refs[-1].get(name)
        if ref is not None:
            return ref[name]
        for frame in reversed(self._frames):
            if name in frame:
                return frame[name]
        raise KeyError(name)

    def __contains__(self, name: object) -> bool:
        return name in self._refs[-1] or any(name in frame for frame in self._frames)

    def set(self, name: str, value: Value) -> None:
        ref = self._refs[-1].get(name)
        if ref is not None:
            ref[name] = value
            return
        self._frames[-1][name] = value

    def clear(self, *names: str) -> None:
        if not names:
            self._frames[-1].clear()
            self._refs[-1].clear()
            return
        for n in names:
            self._frames[-1].pop(n, None)
            self._refs[-1].pop(n, None)

    def names(self) -> Iterator[str]:
        seen: set[str] = set()
        for frame in [self._refs[-1], *reversed(self._frames)]:
            for n in frame:
                if n not in seen:
                    seen.add(n)
                    yield n

    def depth(self) -> int:
        return len(self._frames)
