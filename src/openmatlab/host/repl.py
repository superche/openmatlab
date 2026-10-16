"""REPL shell over Session + Evaluator + DisplayPolicy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from openmatlab.runtime.session import Session


class ReplSession:
    def __init__(self, session: Optional[Session] = None) -> None:
        from openmatlab.runtime.session import Session as Sess

        self.session = session if session is not None else Sess.create_default()

    @property
    def workspace(self):
        return self.session.workspace

    @property
    def display(self):
        return self.session.display

    @property
    def plots(self):
        return self.session.plots

    def feed_input(self, lines) -> None:
        """Queue lines for the K>> / input() prompt (scripted debug sessions, tests, Workbench)."""
        self.session.debugger.inputs.extend(lines)

    def run_line(self, source: str) -> None:
        from openmatlab.lang.parser import parse
        from openmatlab.runtime.evaluator import EvalError, Evaluator

        if self.session.numerics is None:
            raise EvalError('NumPy backend required: pip install -e ".[dev]"')
        self.session.functions.bind_runtime(
            self.session.numerics, self.session.plots
        )
        ev = Evaluator(
            workspace=self.session.workspace,
            functions=self.session.functions,
            numerics=self.session.numerics,
            plots=self.session.plots,
            display=self.display,
        )
        from openmatlab.runtime import debugger as _dbg

        dbg = self.session.debugger
        dbg.display = self.display
        with _dbg.activated(dbg):
            try:
                for stmt in parse(source):
                    ev.eval_stmt(stmt)
            except _dbg.DbQuit:
                dbg.step = None
                _dbg._recompute_on()
