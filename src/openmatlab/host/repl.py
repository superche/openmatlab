"""REPL shell skeleton — interactive loop over a runtime.Session."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from openmatlab.runtime.session import Session


class ReplSession:
    """Interactive shell bound to a Session (workspace + display + plots).

    Evaluation is intentionally not implemented at the architecture stage.
    """

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
        """Parse/eval one line — not implemented (architecture only)."""
        raise NotImplementedError(
            "ReplSession.run_line: language/runtime eval not wired yet"
        )
