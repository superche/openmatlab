"""Cell content indexing + cell() (Issue #66)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import CellIndexExpr
from openmatlab.lang.parser import parse
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_parse_cell_index():
    ix = parse("c{1, 2}")[0].expr
    assert isinstance(ix, CellIndexExpr) and len(ix.indices) == 2


def test_content_index_subscript_and_linear():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("c = {10, 'a'; 20, 30};")
    r.run_line("a = c{1,1}; b = c{1,2};")
    assert float(s.workspace.get("a").backend_buffer().reshape(-1)[0]) == 10
    assert isinstance(s.workspace.get("b"), CharValue) and s.workspace.get("b").text == "a"
    # column-major linear: {1}=10, {2}=20, {3}=a, {4}=30
    r.run_line("u = c{2}; v = c{3}; w = c{4};")
    assert float(s.workspace.get("u").backend_buffer().reshape(-1)[0]) == 20
    assert s.workspace.get("v").text == "a"
    assert float(s.workspace.get("w").backend_buffer().reshape(-1)[0]) == 30


def test_cell_constructor():
    s = Session.create_default()
    ReplSession(s).run_line("d = cell(2, 3); e = cell(2);")
    d = s.workspace.get("d")
    assert isinstance(d, CellValue) and d.shape == (2, 3)
    assert d.get(0, 0).shape == (0, 0)
    assert s.workspace.get("e").shape == (2, 2)


def test_cell_index_errors():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2};")
    with pytest.raises(EvalError, match="exceeds|out of bounds"):
        ReplSession(s).run_line("c{5}")
    with pytest.raises(EvalError, match="expected cell"):
        ReplSession(s).run_line("x = 1; x{1}")


def test_which_cell_builtin():
    s = Session.create_default()
    assert s.functions.which("cell") == "builtin/cell"
