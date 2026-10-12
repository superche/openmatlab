"""Cell paren assign c(i)={v} / c(i,j)=[] (Issue #287)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_paren_assign_cell_rhs():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2, 3}; c(2) = {9};")
    c = s.workspace.get("c")
    assert isinstance(c, CellValue) and c.shape == (1, 3)
    assert float(np.asarray(c.get(0, 1).backend_buffer()).reshape(-1)[0]) == 9


def test_paren_assign_2sub():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2; 3, 4}; c(2, 1) = {8};")
    c = s.workspace.get("c")
    assert float(np.asarray(c.get(1, 0).backend_buffer()).reshape(-1)[0]) == 8


def test_paren_delete_2sub():
    # MATLAB: 2-subscript delete must remove whole rows/columns (#312)
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2; 3, 4}; c(1, :) = [];")
    assert s.workspace.get("c").shape == (1, 2)
    ReplSession(s).run_line("d = {1, 2; 3, 4}; d(:, 2) = [];")
    assert s.workspace.get("d").shape == (2, 1)
    with pytest.raises(EvalError, match="null assignment can have only one non-colon index"):
        ReplSession(s).run_line("e = {1, 2; 3, 4}; e(1, 2) = [];")


def test_paren_assign_rejects_numeric():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2};")
    with pytest.raises(EvalError, match="Conversion to cell from double is not possible"):
        ReplSession(s).run_line("c(1) = 5;")
