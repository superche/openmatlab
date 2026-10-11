"""Bare NaN/Inf/pi as zero-arg constants (Issue #214)."""

from __future__ import annotations

import math

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


def test_nan_in_matrix_and_max():
    assert _s("m = max([1 NaN 3]);", "m") == 3.0


def test_inf_pi_and_neg_inf():
    assert math.isinf(_s("x = Inf;", "x")) and _s("x = Inf;", "x") > 0
    assert math.isinf(_s("x = -Inf;", "x")) and _s("x = -Inf;", "x") < 0
    assert abs(_s("x = pi;", "x") - math.pi) < 1e-15


def test_workspace_shadows_builtin():
    assert _s("NaN = 7; x = NaN;", "x") == 7.0


def test_nan_call_still_works():
    assert math.isnan(_s("x = nan();", "x"))


def test_undefined_still_errors():
    with pytest.raises(EvalError, match="Undefined"):
        ReplSession(Session.create_default()).run_line("x = not_a_thing;")
