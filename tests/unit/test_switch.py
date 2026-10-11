"""switch / case / otherwise (Issue #148)."""

from __future__ import annotations

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import SwitchStmt
from openmatlab.lang.lexer import tokenize
from openmatlab.lang.parser import parse
from openmatlab.lang.tokens import TokenType
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _scalar(session: Session, name: str) -> float:
    return float(session.workspace.get(name).backend_buffer().reshape(-1)[0])


def test_tokens_and_parse():
    types = [t.type for t in tokenize("switch case otherwise end")]
    assert TokenType.KW_SWITCH in types
    assert TokenType.KW_CASE in types
    assert TokenType.KW_OTHERWISE in types
    stmt = parse("switch x\ncase 1\ny=1;\notherwise\ny=0;\nend\n")[0]
    assert isinstance(stmt, SwitchStmt)
    assert len(stmt.cases) == 1
    assert stmt.otherwise is not None


def test_case_match_and_otherwise():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("x = 2;")
    r.run_line("switch x\ncase 1\ny=10;\ncase 2\ny=20;\notherwise\ny=0;\nend")
    assert _scalar(s, "y") == 20
    r.run_line("switch 9\ncase 1\ny=1;\notherwise\ny=99;\nend")
    assert _scalar(s, "y") == 99


def test_multi_case_cell_and_no_fallthrough():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("switch 3\ncase {2,3}\ny=30;\ncase 3\ny=99;\nend")
    assert _scalar(s, "y") == 30  # first match only


def test_no_match_no_otherwise_noop():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("z = 5;")
    r.run_line("switch 99\ncase 1\nz=0;\nend")
    assert _scalar(s, "z") == 5


def test_char_case():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("switch 'b'\ncase 'a'\nc=1;\ncase 'b'\nc=2;\notherwise\nc=3;\nend")
    assert _scalar(s, "c") == 2
