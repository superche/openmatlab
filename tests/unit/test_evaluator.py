"""Evaluator + display (Issue #4)."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from openmatlab.numerics.numpy_backend import NumPyArrayBackend
from openmatlab.runtime.evaluator import EvalError, Evaluator
from openmatlab.runtime.session import Session
from openmatlab.runtime.workspace import Workspace

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture
def ev():
    ws = Workspace()
    return Evaluator(workspace=ws, numerics=NumPyArrayBackend()), ws


def test_arithmetic_and_ans_display(capsys):
    s = Session.create_default()
    from openmatlab.host.repl import ReplSession

    ReplSession(s).run_line("1 + 2 * 3")
    out = capsys.readouterr().out
    assert "7" in out
    assert s.workspace.get("ans").is_scalar()


def test_suppress_semicolon(capsys):
    s = Session.create_default()
    from openmatlab.host.repl import ReplSession

    ReplSession(s).run_line("a = [1 2; 3 4];")
    out = capsys.readouterr().out
    assert out == ""
    a = s.workspace.get("a")
    assert a.shape == (2, 2)


def test_matmul_and_elem(ev):
    evaluator, ws = ev
    evaluator.eval_source("A = [1 2; 3 4]; I = [1 0; 0 1]; B = A * I;")
    import numpy as np

    assert np.allclose(ws.get("B").backend_buffer(), ws.get("A").backend_buffer())
    evaluator.eval_source("C = A .* A;")
    assert float(ws.get("C").backend_buffer()[0, 1]) == 4.0


def test_colon_and_index(ev):
    evaluator, ws = ev
    evaluator.eval_source("r = 1:3;")
    assert ws.get("r").shape == (1, 3)
    evaluator.eval_source("A = [10 20; 30 40]; x = A(2, 1);")
    assert float(ws.get("x").backend_buffer().reshape(-1)[0]) == 30.0


def test_undefined_var(ev):
    evaluator, _ = ev
    with pytest.raises(EvalError, match="Undefined"):
        evaluator.eval_source("z + 1")


def test_cli_eval_matrix(capsys):
    from openmatlab.host.cli import main

    with pytest.raises(SystemExit) as ei:
        main(["-e", "[1 2; 3 4]"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "1" in out and "4" in out
