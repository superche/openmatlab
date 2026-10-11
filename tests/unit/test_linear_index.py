"""Linear (single-subscript) indexing — bug found during #44."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session
from openmatlab.numerics.numpy_backend import NumericsError

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _val(code: str, name: str) -> np.ndarray:
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer())


def test_row_vector_linear():
    assert _val("v = [7 8 9]; x = v(2);", "x")[0, 0] == 8


def test_column_vector_linear_keeps_orientation():
    out = _val("c = [1; 2; 3]; y = c([1 3]);", "y")
    assert out.shape == (2, 1) and list(out.reshape(-1)) == [1, 3]


def test_matrix_linear_is_column_major():
    assert _val("A = [1 2; 3 4]; z = A(2);", "z")[0, 0] == 3
    assert _val("A = [1 2; 3 4]; z = A(3);", "z")[0, 0] == 2


def test_two_subscripts_unchanged():
    assert _val("A = [1 2; 3 4]; w = A(2, 1);", "w")[0, 0] == 3


def test_linear_out_of_range():
    s = Session.create_default()
    with pytest.raises((EvalError, NumericsError)):
        ReplSession(s).run_line("v = [1 2]; v(3)")
