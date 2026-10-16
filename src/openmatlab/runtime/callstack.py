"""MATLAB call stack: one frame per running M-file function or script (Epic #698).

Separate from ``frames`` (which tracks evaluators for evalin/assignin): this stack
records *where* code is (file, name, current line) for ``dbstack``,
``MException.stack``, ``mfilename`` and "Error in ..." reports. The evaluator
updates ``Frame.line`` before each statement, so the cost is one attribute write.
"""

from __future__ import annotations

import contextlib
import contextvars
from dataclasses import dataclass
from pathlib import Path

_STACK: contextvars.ContextVar = contextvars.ContextVar("openmatlab_callstack", default=())


@dataclass
class Frame:
    file: str  # absolute path of the .m file ("" if unknown)
    name: str  # MATLAB stack name: f, f>local, Class.method
    line: int = 0
    ev: object = None  # evaluator running this frame (paused-workspace access, D-E2)


@contextlib.contextmanager
def entering(frame: Frame):
    token = _STACK.set(_STACK.get() + (frame,))
    try:
        yield frame
    finally:
        _STACK.reset(token)


def snapshot() -> tuple:
    """(file, name, line) per frame, innermost first (MATLAB order)."""
    return tuple((f.file, f.name, f.line) for f in reversed(_STACK.get()))


def top():
    st = _STACK.get()
    return st[-1] if st else None


def frame_name(path, name: str, qualname: str | None = None) -> str:
    if qualname:
        return qualname
    stem = Path(path).stem if path else ""
    return name if not stem or stem.lower() == name.lower() else f"{stem}>{name}"


def attach(exc: BaseException) -> None:
    """Record the stack on an exception once, at the innermost statement that raised it."""
    if getattr(exc, "mstack", None) is None:
        try:
            exc.mstack = snapshot()
        except AttributeError:
            pass
