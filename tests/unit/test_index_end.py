"""end as last-index in A(...) (Issue #169)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import ColonExpr, EndExpr, ExprStmt, IndexExpr
from openmatlab.lang.parser import parse
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code: str, name: str):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer())


def _scalar(code: str, name: str) -> float:
    return float(_run(code, name).reshape(-1)[0])


def test_parse_end_in_index():
    ix = parse("A(end)")[0]
    assert isinstance(ix, ExprStmt) and isinstance(ix.expr, IndexExpr)
    assert isinstance(ix.expr.indices[0], EndExpr)
    col = parse("A(1:end)")[0].expr.indices[0]
    assert isinstance(col, ColonExpr) and isinstance(col.stop, EndExpr)


def test_linear_and_2d_end_read():
    assert _scalar("A = [10 20 30 40]; x = A(end);", "x") == 40
    assert _scalar("A = [1 2 3; 4 5 6]; x = A(1,end);", "x") == 3
    assert _scalar("A = [1 2 3; 4 5 6]; x = A(end,1);", "x") == 4
    assert _scalar("A = [10 20 30 40]; x = A(end-1);", "x") == 30


def test_colon_end_and_assign():
    B = _run("A = [1 2 3 4]; B = A(1:end);", "B")
    assert list(B.reshape(-1)) == [1, 2, 3, 4]
    B = _run("A = [1 2 3 4]; A(end) = 9; B = A;", "B")
    assert list(B.reshape(-1)) == [1, 2, 3, 9]
    B = _run("A = zeros(1,4); A(1:end) = [1 2 3 4]; B = A;", "B")
    assert list(B.reshape(-1)) == [1, 2, 3, 4]


def test_bare_end_errors():
    with pytest.raises(Exception):  # ParseError or EvalError
        ReplSession(Session.create_default()).run_line("end")
