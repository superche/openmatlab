"""Delete via A(i)=[] / c(i)=[] (Issue #244)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_vector_delete_and_c06():
    s = Session.create_default()
    ReplSession(s).run_line("v = [1 2 3 4]; v(2) = []; n = numel(v);")
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [[1.0, 3.0, 4.0]]
    assert float(np.asarray(s.workspace.get("n").backend_buffer()).reshape(-1)[0]) == 3
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c06_delete_elements.m");')
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [[1.0, 3.0, 4.0]]


def test_range_and_row_delete():
    s = Session.create_default()
    ReplSession(s).run_line("v = [1 2 3 4]; v(2:3) = [];")
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [[1.0, 4.0]]
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2; 3 4; 5 6]; A(2,:) = [];")
    assert np.asarray(s.workspace.get("A").backend_buffer()).tolist() == [
        [1.0, 2.0],
        [5.0, 6.0],
    ]


def test_cell_paren_delete():
    s = Session.create_default()
    ReplSession(s).run_line("c = {10, 20, 30}; c(2) = [];")
    c = s.workspace.get("c")
    assert isinstance(c, CellValue) and c.shape == (1, 2)
    assert float(np.asarray(c.get(0, 0).backend_buffer()).reshape(-1)[0]) == 10
    assert float(np.asarray(c.get(0, 1).backend_buffer()).reshape(-1)[0]) == 30
