"""Elementwise math builtins (Issue #46)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _g(code: str, name: str) -> np.ndarray:
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer())


def test_unary_shape_preserved():
    out = _g("y = abs([-1 2; -3 4]);", "y")
    assert np.array_equal(out, [[1, 2], [3, 4]])


def test_sqrt_exp_log_sin_cos():
    assert np.allclose(_g("y = sqrt([4 9]);", "y"), [[2, 3]])
    assert np.isclose(_g("y = exp(1);", "y")[0, 0], math.e)
    assert np.isclose(_g("y = log(exp(2));", "y")[0, 0], 2)
    assert np.isclose(_g("y = sin(0) + cos(0);", "y")[0, 0], 1)
    assert _g("y = log(0);", "y")[0, 0] == -math.inf


def test_floor_ceil():
    assert np.array_equal(_g("y = floor([1.5 -1.5]);", "y"), [[1, -2]])
    assert np.array_equal(_g("y = ceil([1.5 -1.5]);", "y"), [[2, -1]])


def test_round_half_away_from_zero():
    out = _g("y = round([2.5 -2.5 0.5 1.4 -0.5]);", "y")
    assert np.array_equal(out, [[3, -3, 1, 1, -1]])


def test_mod_matlab_semantics():
    assert np.array_equal(_g("y = mod([5 -5 5 -5], [3 3 -3 -3]);", "y"), [[2, 1, -1, -2]])
    assert _g("y = mod(7, 0);", "y")[0, 0] == 7
    assert np.array_equal(_g("y = mod(1:5, 2);", "y"), [[1, 0, 1, 0, 1]])


def test_real_domain_errors():
    s = Session.create_default()
    with pytest.raises(EvalError, match="complex"):
        ReplSession(s).run_line("sqrt(-1)")
    with pytest.raises(EvalError, match="complex"):
        ReplSession(s).run_line("log([1 -2])")
    with pytest.raises(EvalError, match="dimensions"):
        ReplSession(s).run_line("mod([1 2 3], [1 2])")
