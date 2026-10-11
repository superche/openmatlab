"""while + break (Issue #34)."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import BreakStmt, WhileStmt
from openmatlab.lang.parser import parse
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_parse_while_break():
    stmts = parse("while x < 3\nx = x + 1\nbreak\nend")
    assert isinstance(stmts[0], WhileStmt)
    assert any(isinstance(s, BreakStmt) for s in stmts[0].body)


def test_eval_while_count():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("x = 0;")
    r.run_line("while x < 4\nx = x + 1;\nend")
    assert float(s.workspace.get("x").backend_buffer().reshape(-1)[0]) == 4.0


def test_eval_while_break():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("x = 0;")
    r.run_line("while 1\nx = x + 1;\nif x == 3\nbreak\nend\nend")
    assert float(s.workspace.get("x").backend_buffer().reshape(-1)[0]) == 3.0


def test_break_in_for():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("s = 0;")
    r.run_line("for i = 1:10\ns = s + i;\nif i == 3\nbreak\nend\nend")
    assert float(s.workspace.get("s").backend_buffer().reshape(-1)[0]) == 6.0
