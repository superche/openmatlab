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
        )
        stmts = parse(source)
        for stmt in stmts:
            value = ev.eval_stmt(stmt)
            suppress = getattr(stmt, "suppress", False)
            if self.display.should_print(suppress):
                name = stmt.name if hasattr(stmt, "name") else None
                self.display.show(value, name=name)
                self.display.bind_ans(value)
            elif hasattr(stmt, "name"):
                # assignment with ; — still done; no ans print
                pass
            else:
                # suppressed expr — still bind ans quietly (MATLAB-like)
                self.display.bind_ans(value)
