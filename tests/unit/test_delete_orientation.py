"""Linear delete orientation / empty-result edges (Issue #312).

Public MATLAB indexing docs: deleting with one subscript keeps a vector's
orientation and reshapes a matrix's remaining elements into a row vector.
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _shape(code: str, name: str = "A"):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    v = s.workspace.get(name)
    return tuple(v.shape) if hasattr(v, "rows") else np.asarray(v.backend_buffer()).shape


def test_matlab_doc_example():
    s = Session.create_default()
    ReplSession(s).run_line("A = [16 2 13; 5 11 8; 9 7 12; 4 14 1]; A(2:2:10) = [];")
    assert np.asarray(s.workspace.get("A").backend_buffer()).tolist() == [[16, 9, 2, 7, 13, 12, 1]]


@pytest.mark.parametrize(
    "code, shape",
    [
        ("A = [1 2 3]; A(A > 0) = [];", (1, 0)),  # all-true on row → 1x0
        ("A = [1; 2; 3]; A(A > 0) = [];", (0, 1)),  # all-true on column → 0x1
        ("A = [1 2; 3 4]; A(true(2)) = [];", (1, 0)),  # matrix → row rule
        ("A = [1 2; 3 4]; A(:) = [];", (0, 0)),  # A(:) = [] clears to 0x0
        ("A = [1 2; 3 4]; A([1 4]) = [];", (1, 2)),
        ("A = [1 2 3]; A(logical([0 0 0])) = [];", (1, 3)),  # all-false: no-op
    ],
)
def test_array_delete_shapes(code, shape):
    assert _shape(code) == shape


@pytest.mark.parametrize(
    "code, shape",
    [
        ("A = {1, 2; 3, 4}; A([1 2]) = [];", (1, 2)),  # matrix cell → row
        ("A = {1, 2}; A(logical([1 1])) = [];", (1, 0)),
        ("A = {1; 2; 3}; A(2) = [];", (2, 1)),
    ],
)
def test_cell_delete_shapes(code, shape):
    assert _shape(code) == shape
