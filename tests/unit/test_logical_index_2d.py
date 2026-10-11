"""2-D logical indexing A(L,:) / A(L1,L2) (Issue #317)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_row_mask_and_col_mask():
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2 3; 4 5 6]; L1 = [1; 0] > 0; r = A(L1, :);")
    assert np.asarray(s.workspace.get("r").backend_buffer()).tolist() == [
        [1.0, 2.0, 3.0]
    ]
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2 3; 4 5 6]; L2 = [1 0 1] > 0; r = A(:, L2);")
    assert np.asarray(s.workspace.get("r").backend_buffer()).tolist() == [
        [1.0, 3.0],
        [4.0, 6.0],
    ]


def test_both_masks_and_assign():
    s = Session.create_default()
    ReplSession(s).run_line(
        "A = [1 2 3; 4 5 6]; L1 = [1; 1] > 0; L2 = [0 1 0] > 0; r = A(L1, L2);"
    )
    assert np.asarray(s.workspace.get("r").backend_buffer()).tolist() == [
        [2.0],
        [5.0],
    ]
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2; 3 4]; L = [1; 0] > 0; A(L, :) = 0;")
    assert np.asarray(s.workspace.get("A").backend_buffer()).tolist() == [
        [0.0, 0.0],
        [3.0, 4.0],
    ]


def test_c07_thickened():
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c07_logical_indexing.m");')
    assert np.asarray(s.workspace.get("r").backend_buffer()).tolist() == [
        [1.0, 2.0, 3.0]
    ]
