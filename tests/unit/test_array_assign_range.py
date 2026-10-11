"""Range / non-scalar indexed assignment (Issue #159)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code: str, name: str):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer())


def test_linear_range_vector_rhs():
    B = _run("A = [1 2 3 4]; A(1:3) = [10 20 30]; B = A;", "B")
    assert list(B.reshape(-1, order="F")) == [10, 20, 30, 4]


def test_linear_range_scalar_broadcast():
    B = _run("A = zeros(1,4); A(2:4) = 7; B = A;", "B")
    assert list(B.reshape(-1)) == [0, 7, 7, 7]


def test_two_sub_column_and_block():
    B = _run("A = [1 2; 3 4]; A(1:2,1) = [9;8]; B = A;", "B")
    assert B.tolist() == [[9.0, 2.0], [8.0, 4.0]]
    B = _run("A = zeros(2); A(1:2,1:2) = [1 2; 3 4]; B = A;", "B")
    assert B.tolist() == [[1.0, 2.0], [3.0, 4.0]]


def test_numel_mismatch_errors():
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2 3];")
    with pytest.raises(EvalError, match="numel"):
        ReplSession(s).run_line("A(1:2) = [1 2 3];")


def test_scalar_assign_still_works():
    B = _run("A = [1 2; 3 4]; A(2,1) = 9; B = A;", "B")
    assert B.tolist() == [[1.0, 2.0], [9.0, 4.0]]
