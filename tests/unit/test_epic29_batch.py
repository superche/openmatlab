"""Epic #29 batch: constants, EvalError wrap, cell end/colon, C11 (Issue #334)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_eps_realmax_realmin():
    s = Session.create_default()
    ReplSession(s).run_line("e = eps; M = realmax; m = realmin;")
    assert float(np.asarray(s.workspace.get("e").backend_buffer()).reshape(-1)[0]) > 0
    assert float(np.asarray(s.workspace.get("M").backend_buffer()).reshape(-1)[0]) > 1e300
    assert float(np.asarray(s.workspace.get("m").backend_buffer()).reshape(-1)[0]) > 0


def test_power_wraps_eval_error():
    s = Session.create_default()
    with pytest.raises(EvalError, match="power|square"):
        ReplSession(s).run_line("x = [1 2; 3 4; 5 6]^2;")


def test_cell_end_and_colon():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2, 3}; x = c{end};")
    assert float(np.asarray(s.workspace.get("x").backend_buffer()).reshape(-1)[0]) == 3
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2; 3, 4}; x = c{:, 1};")
    x = s.workspace.get("x")
    assert isinstance(x, CellValue) and x.shape == (2, 1)


def test_step_colon_and_c11():
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2 3; 4 5 6]; r = A(1:2:end, :);")
    assert np.asarray(s.workspace.get("r").backend_buffer()).tolist() == [[1.0, 2.0, 3.0]]
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c11_scalar_power_script.m");')
    assert np.asarray(s.workspace.get("B").backend_buffer()).tolist() == [
        [1.0, 2.0],
        [0.0, 1.0],
    ]
