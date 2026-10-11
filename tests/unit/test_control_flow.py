"""Minimal if/for control flow (Issue #22)."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import ForStmt, IfStmt
from openmatlab.lang.parser import parse
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_parse_if_else():
    src = "if x == 1\ny = 2\nelse\ny = 3\nend"
    stmts = parse(src)
    assert len(stmts) == 1
    assert isinstance(stmts[0], IfStmt)
    assert stmts[0].else_body is not None


def test_parse_for():
    stmts = parse("for i = 1:3\ns = s + i\nend")
    assert isinstance(stmts[0], ForStmt)
    assert stmts[0].var == "i"


def test_eval_if_else():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("x = 1;")
    r.run_line("if x == 1\ny = 10\nelse\ny = 20\nend")
    assert float(s.workspace.get("y").backend_buffer().reshape(-1)[0]) == 10.0
    r.run_line("x = 0;")
    r.run_line("if x == 1\ny = 10\nelse\ny = 20\nend")
    assert float(s.workspace.get("y").backend_buffer().reshape(-1)[0]) == 20.0


def test_eval_elseif():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("x = 2;")
    r.run_line(
        "if x == 1\ny = 1\nelseif x == 2\ny = 2\nelse\ny = 3\nend"
    )
    assert float(s.workspace.get("y").backend_buffer().reshape(-1)[0]) == 2.0


def test_eval_for_sum():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("s = 0;")
    r.run_line("for i = 1:4\ns = s + i;\nend")
    assert float(s.workspace.get("s").backend_buffer().reshape(-1)[0]) == 10.0
