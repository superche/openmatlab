"""Cell literals + CellValue (Issue #65)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.display import _format_value
from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import CellLiteral
from openmatlab.lang.parser import ParseError, parse
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_parse_cell():
    lit = parse("c = {1, 2; 3, 4}")[0].value
    assert isinstance(lit, CellLiteral)
    assert len(lit.rows) == 2 and len(lit.rows[0]) == 2
    assert isinstance(parse("e = {}")[0].value, CellLiteral)


def test_parse_ragged_cell_errors():
    with pytest.raises(ParseError, match="ragged"):
        parse("{1, 2; 3}")


def test_eval_mixed_cell():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 'a'; 2, [3 4]};")
    c = s.workspace.get("c")
    assert isinstance(c, CellValue) and c.shape == (2, 2)
    assert isinstance(c.get(0, 1), CharValue) and c.get(0, 1).text == "a"
    assert np.array_equal(np.asarray(c.get(1, 1).backend_buffer()), [[3, 4]])


def test_empty_and_row_cell():
    s = Session.create_default()
    ReplSession(s).run_line("e = {}; r = {1 2 3};")
    assert s.workspace.get("e").shape == (0, 0)
    assert s.workspace.get("r").shape == (1, 3)


def test_nested_cell():
    s = Session.create_default()
    ReplSession(s).run_line("z = {{7}, 'x'};")
    z = s.workspace.get("z")
    assert isinstance(z.get(0, 0), CellValue) and z.get(0, 0).get(0, 0).is_scalar()


def test_cell_display():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 'a'};")
    text = _format_value(s.workspace.get("c"))
    assert "1x2 cell" in text
    assert "(1,2)" in text
