"""Comma as statement separator (Issue #407)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import Assign, ForStmt, IfStmt, SwitchStmt
from openmatlab.lang.parser import parse
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code: str):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return lambda n: np.asarray(s.workspace.get(n).backend_buffer()).reshape(-1).tolist()


def test_top_level_comma_separates_and_keeps_display():
    stmts = parse("a=1, b=2; c=3")
    assert [type(x) for x in stmts] == [Assign, Assign, Assign]
    assert [x.suppress for x in stmts] == [False, True, False]


def test_comma_after_block_headers_and_bodies():
    stmts = parse("for i=1:3, x=i; end, if x==3, y=1; else, y=0; end")
    assert isinstance(stmts[0], ForStmt) and isinstance(stmts[1], IfStmt)
    stmts = parse("switch 2, case 1, y=1; case {2,3}, y=2; otherwise, y=0; end")
    assert isinstance(stmts[0], SwitchStmt) and len(stmts[0].cases) == 2


def test_comma_one_liners_evaluate():
    get = _ws("s=0; for i=1:3, s=s+i; end, if s==6, t=1; else, t=0; end")
    assert get("s") == [6.0] and get("t") == [1.0]
    get = _ws("switch 3, case 1, y=1; case {2,3}, y=2; otherwise, y=0; end")
    assert get("y") == [2.0]
    get = _ws("k=0; while k<2, k=k+1; end")
    assert get("k") == [2.0]


def test_comma_inside_brackets_and_calls_unchanged():
    get = _ws("x=[1, 2]; A=zeros(2, 3); n=numel(A)")
    assert get("x") == [1.0, 2.0] and get("n") == [6.0]
