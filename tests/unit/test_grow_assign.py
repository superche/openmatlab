"""Grow-on-assign A(i)= / c{i}= (Issue #254)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_vector_grow_c08():
    s = Session.create_default()
    ReplSession(s).run_line("v = [1 2]; v(4) = 7; n = numel(v);")
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [
        [1.0, 2.0, 0.0, 7.0]
    ]
    assert float(np.asarray(s.workspace.get("n").backend_buffer()).reshape(-1)[0]) == 4
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c08_grow_on_assign.m");')
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [
        [1.0, 2.0, 0.0, 7.0]
    ]


def test_matrix_2sub_grow():
    s = Session.create_default()
    ReplSession(s).run_line("A = zeros(2); A(3,4) = 9;")
    A = np.asarray(s.workspace.get("A").backend_buffer())
    assert A.shape == (3, 4) and A[2, 3] == 9


def test_cell_content_grow():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1}; c{3} = 9;")
    c = s.workspace.get("c")
    assert isinstance(c, CellValue) and c.shape == (1, 3)
    assert float(np.asarray(c.get(0, 2).backend_buffer()).reshape(-1)[0]) == 9
