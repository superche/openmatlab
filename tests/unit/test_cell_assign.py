"""Cell content assignment c{i}=v (Issue #103)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import CellAssign
from openmatlab.lang.parser import parse
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_parse_cell_assign():
    stmt = parse("c{1,2} = 5")[0]
    assert isinstance(stmt, CellAssign)


def test_assign_subscript_and_linear():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("c = {1, 'a'; 2, 3};")
    r.run_line("c{1,2} = 'z';")
    r.run_line("c{2} = 7;")  # linear 2 → (2,1) == get(1,0)
    assert isinstance(s.workspace.get("c").get(0, 1), CharValue)
    assert s.workspace.get("c").get(0, 1).text == "z"
    assert float(s.workspace.get("c").get(1, 0).backend_buffer().reshape(-1)[0]) == 7


def test_assign_nested_cell():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("c = {1, 2};")
    r.run_line("c{2} = {9};")
    inner = s.workspace.get("c").get(0, 1)
    assert inner.matlab_class() == "cell"
    assert float(inner.get(0, 0).backend_buffer().reshape(-1)[0]) == 9


def test_assign_oob():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2};")
    with pytest.raises(EvalError, match="exceeds|out of bounds"):
        ReplSession(s).run_line("c{5} = 1;")
