"""Call-frame stack for evalin/assignin (Epic C11).

Each time an evaluator calls a function (M-file, local function, handle or
builtin), it pushes itself for the duration of the call. Inside the callee:

- the **caller** workspace is the evaluator on top of the stack;
- the **base** workspace is the bottom entry (the command-line evaluator).

When the stack is empty, the running evaluator is itself the base, and its
caller is also the base (MATLAB: evalin('caller', ...) at the prompt runs in
the base workspace). The stack lives in a ContextVar, so threads and nested
contexts stay isolated. Push and pop are balanced through a context manager,
so errors unwind it.
"""

from __future__ import annotations

import contextlib
import contextvars

_STACK: contextvars.ContextVar = contextvars.ContextVar("openmatlab_frames", default=())


@contextlib.contextmanager
def calling(ev):
    token = _STACK.set(_STACK.get() + (ev,))
    try:
        yield
    finally:
        _STACK.reset(token)


@contextlib.contextmanager
def isolated():
    """A fresh stack, e.g. for a nested Session (str2num): its base is itself."""
    token = _STACK.set(())
    try:
        yield
    finally:
        _STACK.reset(token)


def caller(ev):
    st = _STACK.get()
    return st[-1] if st else ev


def base(ev):
    st = _STACK.get()
    return st[0] if st else ev


def depth() -> int:
    return len(_STACK.get())
