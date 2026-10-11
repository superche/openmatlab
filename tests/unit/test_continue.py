"""continue in for/while (Issue #127)."""

from __future__ import annotations

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import ContinueStmt
from openmatlab.lang.lexer import tokenize
from openmatlab.lang.parser import parse
from openmatlab.lang.tokens import TokenType
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_token_and_parse():
    assert TokenType.KW_CONTINUE in [t.type for t in tokenize("continue")]
    assert isinstance(parse("continue")[0], ContinueStmt)


def test_continue_in_for():
    s = Session.create_default()
    ReplSession(s).run_line(
        "s = 0; for i = 1:5; if i == 3; continue; end; s = s + i; end;"
    )
    assert float(s.workspace.get("s").backend_buffer().reshape(-1)[0]) == 12


def test_continue_in_while():
    s = Session.create_default()
    ReplSession(s).run_line(
        "t = 0; n = 0; while n < 5; n = n + 1; if n == 2; continue; end; t = t + n; end;"
    )
    assert float(s.workspace.get("t").backend_buffer().reshape(-1)[0]) == 13


def test_continue_nested_innermost_only():
    s = Session.create_default()
    ReplSession(s).run_line(
        "s = 0; for i = 1:3; for j = 1:3; if j == 2; continue; end; s = s + 1; end; end;"
    )
    assert float(s.workspace.get("s").backend_buffer().reshape(-1)[0]) == 6


def test_break_still_works():
    s = Session.create_default()
    ReplSession(s).run_line("s = 0; for i = 1:5; if i == 3; break; end; s = s + i; end;")
    assert float(s.workspace.get("s").backend_buffer().reshape(-1)[0]) == 3


def test_continue_outside_loop_errors():
    s = Session.create_default()
    with pytest.raises(EvalError, match="continue outside"):
        ReplSession(s).run_line("continue;")
    with pytest.raises(EvalError, match="break outside"):
        ReplSession(s).run_line("break;")
