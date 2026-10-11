"""logical / true / false + 2-D logical delete (Issue #327)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_logical_true_false():
    s = Session.create_default()
    ReplSession(s).run_line("x = true; y = false; z = logical([1 0 2]); t = true(1, 3);")
    assert s.workspace.get("x").matlab_class() == "logical"
    assert float(np.asarray(s.workspace.get("x").backend_buffer()).reshape(-1)[0]) == 1
    assert float(np.asarray(s.workspace.get("y").backend_buffer()).reshape(-1)[0]) == 0
    assert np.asarray(s.workspace.get("z").backend_buffer()).tolist() == [[True, False, True]]
    assert np.asarray(s.workspace.get("t").backend_buffer()).tolist() == [[True, True, True]]


def test_logical_row_delete():
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2; 3 4; 5 6]; L = [1; 0; 1] > 0; A(L, :) = [];")
    assert np.asarray(s.workspace.get("A").backend_buffer()).tolist() == [[3.0, 4.0]]


def test_logical_col_delete_via_full_rows():
    s = Session.create_default()
    ReplSession(s).run_line(
        "A = [1 2 3; 4 5 6]; L1 = [1; 1] > 0; L2 = [1 0 1] > 0; A(L1, L2) = [];"
    )
    assert np.asarray(s.workspace.get("A").backend_buffer()).tolist() == [[2.0], [5.0]]
