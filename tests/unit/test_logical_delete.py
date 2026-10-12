"""Logical-mask delete A(L)=[] (Issue #307)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_vector_expr_and_mask():
    s = Session.create_default()
    ReplSession(s).run_line("v = [1 2 3 4]; v(v > 2) = [];")
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [[1.0, 2.0]]
    s = Session.create_default()
    ReplSession(s).run_line("v = [1 2 3 4]; L = v > 2; v(L) = [];")
    assert np.asarray(s.workspace.get("v").backend_buffer()).tolist() == [[1.0, 2.0]]


def test_matrix_becomes_row():
    # MATLAB: linear delete from a matrix reshapes the rest to a row vector (#312)
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2; 3 4]; A(A > 2) = [];")
    A = np.asarray(s.workspace.get("A").backend_buffer())
    assert A.shape == (1, 2) and A.tolist() == [[1.0, 2.0]]


def test_c06_includes_logical():
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c06_delete_elements.m");')
    assert np.asarray(s.workspace.get("v2").backend_buffer()).tolist() == [[1.0, 2.0]]
    assert float(np.asarray(s.workspace.get("n2").backend_buffer()).reshape(-1)[0]) == 2
