"""zeros/ones/eye size-vector form (Issue #179)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _shape(code: str, name: str = "A"):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer()).shape


def test_size_vector_2():
    assert _shape("A = zeros([2 3]);") == (2, 3)
    assert _shape("A = ones([2 3]);") == (2, 3)
    assert _shape("A = zeros([2, 3]);") == (2, 3)


def test_scalar_and_one_element_matrix_square():
    assert _shape("A = zeros(4);") == (4, 4)
    assert _shape("A = zeros([4]);") == (4, 4)  # 1×1 size matrix ≡ scalar


def test_two_arg_and_eye_vector():
    assert _shape("A = zeros(2, 3);") == (2, 3)
    assert _shape("A = eye([2 3]);") == (2, 3)
    s = Session.create_default()
    ReplSession(s).run_line("A = eye([2 3]);")
    assert np.allclose(s.workspace.get("A").backend_buffer(), np.eye(2, 3))


def test_nd_size_vector_errors():
    s = Session.create_default()
    with pytest.raises(EvalError, match="N-D|size"):
        ReplSession(s).run_line("A = zeros([2 3 4]);")
