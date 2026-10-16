"""Debug engine: breakpoints, stepping, paused K>> prompt (M11 D-E2, Epic #699).

Pause model (docs/design/EPIC-699-pause-model.md): a re-entrant nested REPL. The
statement hook in ``Evaluator.eval_stmt`` calls ``on_statement``; on a hit,
``pause`` reads ``K>>`` lines and evaluates them in the active frame's evaluator
until ``dbcont`` / ``dbstep`` / ``dbquit``.
"""

from __future__ import annotations

import contextlib
import contextvars
import sys
import weakref
from collections import deque
from pathlib import Path
from typing import Dict, Optional

from openmatlab.runtime import callstack

ON = False  # any session has breakpoints or a pending step: the hook is consulted
_ACTIVE: contextvars.ContextVar = contextvars.ContextVar("openmatlab_debugger", default=None)
_ALL = weakref.WeakSet()  # every live Debugger, for ON recomputation (dead sessions drop out)


class DbQuit(BaseException):
    """dbquit: unwinds to the prompt; not catchable by MATLAB try/catch."""


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def active() -> Optional["Debugger"]:
    return _ACTIVE.get()


@contextlib.contextmanager
def activated(dbg):
    tok = _ACTIVE.set(dbg)
    try:
        yield dbg
    finally:
        _ACTIVE.reset(tok)


def _recompute_on():
    global ON
    busy = [d for d in _ALL if d.bps or d.step is not None or d.cond_stops]
    if busy and active() not in busy:  # only other sessions keep the hook on: drop dead (cyclic) ones first
        import gc

        gc.collect()
        busy = [d for d in _ALL if d.bps or d.step is not None or d.cond_stops]
    ON = bool(busy)


def statement_lines(stmts) -> list:
    """Every statement line in a parsed file (nested blocks included), sorted."""
    from dataclasses import fields, is_dataclass

    out = set()

    def walk(node):
        if isinstance(node, (list, tuple)):
            for x in node:
                walk(x)
            return
        if not is_dataclass(node):
            return
        ln = getattr(node, "_line", None)
        if ln is not None and type(node).__name__ not in ("FunctionDef", "LocalFunction"):
            out.add(ln)
        for f in fields(node):
            v = getattr(node, f.name)
            if isinstance(v, (list, tuple)) or is_dataclass(v):
                walk(v)

    walk(list(stmts))
    return sorted(out)


class Debugger:
    def __init__(self):
        self.bps: Dict[str, Dict[int, Optional[str]]] = {}  # file -> line -> condition
        self.names: Dict[str, str] = {}  # file -> function name (for dbstatus)
        self.step = None  # (mode, base_depth, remaining)
        self.cond_stops: Dict[str, list] = {}  # 'error'/'caught error'/'warning'/'naninf' -> ids (D-E3)
        self.inputs: deque = deque()
        self.paused = []  # stack of PauseState (nested pauses)
        self.out = None  # stream for pause messages (None: sys.stdout)
        self.display = None
        self.read_line = None  # optional callable(prompt) -> str (Workbench); else console input()
        _ALL.add(self)

    # -- breakpoints -----------------------------------------------------------
    def set_bp(self, file: str, name: str, line: int, cond: Optional[str]):
        self.bps.setdefault(file, {})[line] = cond
        self.names[file] = name
        _recompute_on()

    def clear(self, file: Optional[str] = None, line: Optional[int] = None):
        if file is None:
            self.bps.clear()
        elif line is None:
            self.bps.pop(file, None)
        else:
            self.bps.get(file, {}).pop(line, None)
            if not self.bps.get(file):
                self.bps.pop(file, None)
        _recompute_on()

    def request_step(self, mode: str, n: int = 1):
        st = self.paused[-1] if self.paused else None
        depth = st.depth if st else len(callstack._STACK.get())
        self.step = (mode, depth, n)
        _recompute_on()

    # -- hook --------------------------------------------------------------------
    def on_statement(self, ev, frame, stmt):
        line = getattr(stmt, "_line", None)
        if line is None:
            return
        depth = len(callstack._STACK.get())
        hit = False
        if self.step is not None:
            mode, base, n = self.step
            if (mode == "in") or (mode == "step" and depth <= base) or (mode == "out" and depth < base):
                n -= 1
                if n <= 0:
                    hit = True
                    self.step = None
                    _recompute_on()
                else:
                    self.step = (mode, base, n)
        if not hit:
            lines = self.bps.get(frame.file)
            if lines and line in lines:
                cond = lines[line]
                hit = cond is None or self._truthy(ev, cond)
        if hit:
            self.pause(ev, frame, line)

    def on_return(self):
        """dbstep out: pause in the caller at the call line as soon as the function returns (MATLAB)."""
        if self.step is None or self.step[0] != "out":
            return
        st = callstack._STACK.get()
        _mode, base, n = self.step
        if not st or len(st) >= base:
            return
        if n > 1:
            self.step = ("out", len(st) + 1, n - 1)
            return
        self.step = None
        _recompute_on()
        frame = st[-1]
        if getattr(frame, "ev", None) is not None and frame.line:
            self.pause(frame.ev, frame, frame.line)

    def _truthy(self, ev, cond: str) -> bool:
        import numpy as np

        from openmatlab.lang.parser import parse
        from openmatlab.runtime.evaluator import Evaluator

        try:
            e = Evaluator(workspace=ev.workspace, functions=ev.functions, numerics=ev.numerics, plots=ev.plots)
            v = e.eval_expr(parse(cond, commands=False)[0].expr)
            b = np.asarray(v.backend_buffer())
            return b.size > 0 and bool(np.all(b != 0))
        except Exception:
            return False  # MATLAB: an invalid condition does not stop

    # -- pause loop ----------------------------------------------------------------
    def _write(self, text):
        (self.out or sys.stdout).write(text)

    def _next_line(self) -> Optional[str]:
        if self.inputs:
            return self.inputs.popleft()
        if self.read_line is not None:
            return self.read_line("K>> ")
        try:
            return input("K>> ")
        except EOFError:
            return None

    def pause(self, ev, frame, line):
        st = PauseState(self, ev, frame, line)
        self.paused.append(st)
        try:
            src = _source_line(frame.file, line)
            self._write(f"{line}   {src}\n" if src is not None else f"{line}\n")
            st.loop()
        finally:
            self.paused.pop()


class PauseState:
    def __init__(self, dbg, ev, frame, line):
        self.dbg = dbg
        self.frames = list(callstack._STACK.get())  # outermost first
        self.depth = len(self.frames)
        self.idx = len(self.frames) - 1  # active frame (dbup decreases; -1 = base workspace)
        self.base_ev = _base_evaluator(ev)
        self.resume = None
        self.line = line

    def active_ev(self):
        if self.idx < 0:
            return self.base_ev
        return getattr(self.frames[self.idx], "ev", None) or self.base_ev

    def loop(self):
        from openmatlab.lang.lexer import LexerError
        from openmatlab.lang.parser import ParseError, parse
        from openmatlab.runtime.evaluator import EvalError, Evaluator

        while self.resume is None:
            text = self.dbg._next_line()
            if text is None:
                raise DbQuit()
            if not text.strip():
                continue
            src = self.active_ev()
            ev = Evaluator(workspace=src.workspace, functions=src.functions, numerics=src.numerics, plots=src.plots,
                           display=self.dbg.display)
            ev._frame = None
            try:
                for stmt in parse(text):
                    ev.eval_stmt(stmt)
                    if self.resume is not None:
                        break
            except (LexerError, ParseError, EvalError) as exc:
                self.dbg._write(f"error: {exc}\n")
            except DbQuit:
                raise
            except Exception as exc:  # never a traceback at K>>
                self.dbg._write(f"error: internal error ({type(exc).__name__}): {exc}\n")
        if self.resume == "quit":
            raise DbQuit()


def _base_evaluator(ev):
    from openmatlab.runtime import frames

    return frames.base(ev)


def _source_line(file, line):
    try:
        return Path(file).read_text().splitlines()[line - 1].strip()
    except (OSError, IndexError, ValueError):
        return None
