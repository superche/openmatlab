"""Multi-return assign [a,b] = f(...) (Issue #21)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import MultiAssign
from openmatlab.lang.parser import parse
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_parse_multi_assign():
    stmts = parse("[a, b] = swap(1, 2)")
    assert len(stmts) == 1
    assert isinstance(stmts[0], MultiAssign)
    assert list(stmts[0].names) == ["a", "b"]


def test_matrix_literal_not_multi_assign():
    stmts = parse("M = [1 2; 3 4]")
    assert not isinstance(stmts[0], MultiAssign)


def test_eval_multi_return(tmp_path: Path):
    (tmp_path / "swap.m").write_text(
        "function [a, b] = swap(x, y)\na = y;\nb = x;\nend\n"
    )
    s = Session.create_default()
    ReplSession(s).run_line(f'addpath("{tmp_path}")')
    ReplSession(s).run_line("[u, v] = swap(1, 2);")
    assert float(s.workspace.get("u").backend_buffer().reshape(-1)[0]) == 2.0
    assert float(s.workspace.get("v").backend_buffer().reshape(-1)[0]) == 1.0


def test_single_bracket_assign(tmp_path: Path):
    (tmp_path / "iden.m").write_text(
        "function y = iden(x)\ny = x;\nend\n"
    )
    s = Session.create_default()
    ReplSession(s).run_line(f'addpath("{tmp_path}")')
    ReplSession(s).run_line("[z] = iden(9);")
    assert float(s.workspace.get("z").backend_buffer().reshape(-1)[0]) == 9.0
