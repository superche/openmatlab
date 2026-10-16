"""Workbench debug controller (M11 D-E4, Epic #701).

Option B of the pause-model design (docs/design/EPIC-699-pause-model.md) layered on
the D-E2 engine: user code runs in a worker thread; the engine's paused-input source
(``Debugger.read_line``) blocks on a queue that the toolbar and the Command Window
feed. Every toolbar action sends one debug command and waits until the code pauses
again or finishes, so the headless model is deterministic.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import List, Optional, Tuple

DEBUG_TOOLBAR: Tuple[str, ...] = ("Continue", "Step", "Step In", "Step Out", "Quit Debugging")
_TIMEOUT = 60.0


class DebugError(RuntimeError):
    """Misuse of the debug controller (for example Step while not paused)."""


class DebugController:
    def __init__(self, command_window):
        self.cw = command_window
        self.session = command_window.session
        self._cmds: "queue.Queue[str]" = queue.Queue()
        self._cv = threading.Condition()
        self._state = "idle"  # idle | running | paused
        self._worker: Optional[threading.Thread] = None
        self.listeners: list = []  # callables(state) -> None (tk refresh)

    # -- engine side (worker thread) -------------------------------------------
    def _read_line(self, prompt: str) -> Optional[str]:
        self._set("paused")
        line = self._cmds.get()
        self._set("running")
        return line

    def _set(self, state: str) -> None:
        with self._cv:
            self._state = state
            self._cv.notify_all()
        for fn in list(self.listeners):
            try:
                fn(state)
            except Exception:
                pass

    def _work(self, source: str, history: bool = True) -> None:
        dbg = self.session.debugger
        dbg.read_line = self._read_line
        dbg.out = self.cw._stream
        try:
            self.cw.eval(source, history=history)
        except Exception as exc:  # never a traceback: MATLAB error text in the Command Window
            self.cw._stream.write(self.cw.error_text(exc) + "\n")
        finally:
            dbg.read_line = None
            dbg.out = None
            self._set("idle")

    def _wait_settled(self) -> None:
        with self._cv:
            ok = self._cv.wait_for(lambda: self._state != "running", timeout=_TIMEOUT)
        if not ok:
            raise DebugError("debug: timed out waiting for the code to pause or finish")
        if self._state == "idle" and self._worker is not None:
            self._worker.join(timeout=_TIMEOUT)
            self._worker = None

    # -- UI side ---------------------------------------------------------------
    def run(self, source: str, history: bool = True) -> None:
        """Run code (Command Window line or editor Run) so breakpoints can pause it."""
        if self._state != "idle":
            raise DebugError("debug: code is already running; Continue or Quit Debugging first")
        self._state = "running"
        self._worker = threading.Thread(target=self._work, args=(source, history), daemon=True, name="openmatlab-run")
        self._worker.start()
        self._wait_settled()

    def is_paused(self) -> bool:
        return self._state == "paused"

    def send(self, line: str) -> None:
        """Feed one K>> line (a debug command or an expression) and wait for the result."""
        if self._state != "paused":
            raise DebugError("debug: not paused")
        with self._cv:
            self._state = "running"
        self._cmds.put(line)
        self._wait_settled()

    def continue_(self) -> None:
        self.send("dbcont")

    def step(self) -> None:
        self.send("dbstep")

    def step_in(self) -> None:
        self.send("dbstep in")

    def step_out(self) -> None:
        self.send("dbstep out")

    def quit(self) -> None:
        self.send("dbquit")

    def _pause(self):
        p = self.session.debugger.paused
        return p[-1] if (p and self._state == "paused") else None

    def stack(self) -> List[Tuple[str, str, int]]:
        """(name, file, line) per frame, current frame first (dbstack order)."""
        st = self._pause()
        if st is None:
            return []
        out = []
        for k, f in enumerate(reversed(st.frames)):
            out.append((f.name, f.file, st.line if k == 0 else int(f.line)))
        return out

    def selected_frame(self) -> int:
        st = self._pause()
        return 0 if st is None else (len(st.frames) - 1 - st.idx)

    def select_frame(self, k: int) -> None:
        """Stack selector: 0 is the current frame, 1 its caller, ... (same as dbup k times)."""
        st = self._pause()
        if st is None:
            raise DebugError("debug: not paused")
        if not 0 <= k < len(st.frames):
            raise DebugError(f"debug: no stack frame {k}")
        st.idx = len(st.frames) - 1 - k
        for fn in list(self.listeners):
            try:
                fn("paused")
            except Exception:
                pass

    def current_line(self) -> Optional[int]:
        """Line of the selected frame (the editor's current-line marker), None when not paused."""
        s = self.stack()
        return s[self.selected_frame()][2] if s else None

    def current_file(self) -> Optional[Path]:
        s = self.stack()
        return Path(s[self.selected_frame()][1]) if s else None

    def active_workspace(self):
        st = self._pause()
        return st.active_ev().workspace if st is not None else self.session.workspace


def toggle_breakpoint(session, path: Path, line: int) -> None:
    """Gutter click: clear the breakpoint on that (snapped) line if set, else dbstop there."""
    from openmatlab.libs.debug_builtins import _exec_lines

    d = session.debugger
    p = str(Path(path).resolve())
    lines, _first = _exec_lines(p)
    after = [x for x in lines if x >= line]
    if not after:
        raise DebugError(f"Breakpoint cannot be set at line {line}: no executable line at or after it.")
    target = after[0]
    if target in d.bps.get(p, {}):
        d.clear(p, target)
    else:
        d.set_bp(p, Path(p).stem, target, None)


def breakpoints(session, path: Path):
    """Breakpoint lines as a MATLAB row vector, like ``dbstatus(file).line``: 1×N, or 0×0 when none."""
    import numpy as np

    lines = sorted(session.debugger.bps.get(str(Path(path).resolve()), {}))
    return np.array([lines], dtype=int) if lines else np.zeros((0, 0), dtype=int)
