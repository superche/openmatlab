"""Scalar / square-matrix power ^ (Issue #224)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _s(code: str, name: str) -> float:
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return float(np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1)[0])


def _a(code: str, name: str):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer())


def test_scalar_power():
    assert _s("x = 2^3;", "x") == 8
    assert _s("i = 3; x = i^2;", "x") == 9


def test_square_matrix_power():
    assert _a("A = [1 1; 0 1]; B = A^3;", "B").tolist() == [[1.0, 3.0], [0.0, 1.0]]


def test_elementwise_unchanged():
    assert _a("x = [2 3].^[2 3];", "x").tolist() == [[4.0, 27.0]]


def test_non_square_errors():
    with pytest.raises(Exception, match="matrix power|square"):
        ReplSession(Session.create_default()).run_line("x = [1 2]^2;")


def test_c11_script():
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c11_scalar_power_script.m");')
    assert float(np.asarray(s.workspace.get("x").backend_buffer()).reshape(-1)[0]) == 14
    assert float(np.asarray(s.workspace.get("y").backend_buffer()).reshape(-1)[0]) == 3
