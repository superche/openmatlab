"""Parentheses cell indexing c(i) → sub-cell (Issue #104)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_paren_returns_one_by_one_cell():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("c = {10, 'a'; 20, 30};")
    r.run_line("s = c(1, 2); t = c(2);")
    s_cell = s.workspace.get("s")
    assert isinstance(s_cell, CellValue) and s_cell.shape == (1, 1)
    assert isinstance(s_cell.get(0, 0), CharValue) and s_cell.get(0, 0).text == "a"
    t_cell = s.workspace.get("t")
    assert isinstance(t_cell, CellValue)
    assert float(t_cell.get(0, 0).backend_buffer().reshape(-1)[0]) == 20


def test_paren_vs_content():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("c = {1, 'z'};")
    r.run_line("a = c{1,2}; b = c(1,2);")
    assert isinstance(s.workspace.get("a"), CharValue)
    assert isinstance(s.workspace.get("b"), CellValue)


def test_array_paren_unchanged():
    s = Session.create_default()
    ReplSession(s).run_line("A = [10 20]; x = A(2);")
    assert float(s.workspace.get("x").backend_buffer().reshape(-1)[0]) == 20


def test_paren_oob():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2};")
    with pytest.raises(EvalError, match="exceeds|out of bounds"):
        ReplSession(s).run_line("c(5)")
