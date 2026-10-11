"""zeros/ones/eye/linspace + size/numel/length (Issue #44)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code: str) -> Session:
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _get(s: Session, name: str) -> np.ndarray:
    return np.asarray(s.workspace.get(name).backend_buffer())


def test_zeros_ones_shapes():
    s = _run("a = zeros(2, 3); b = ones(2); c = zeros();")
    assert _get(s, "a").shape == (2, 3) and not _get(s, "a").any()
    assert _get(s, "b").shape == (2, 2) and (_get(s, "b") == 1).all()
    assert _get(s, "c").shape == (1, 1)


def test_eye_square_and_rect():
    s = _run("I = eye(3); R = eye(2, 3);")
    assert np.array_equal(_get(s, "I"), np.eye(3))
    assert np.array_equal(_get(s, "R"), np.eye(2, 3))


def test_linspace_default_and_n():
    s = _run("x = linspace(0, 1, 5); y = linspace(0, 1);")
    assert np.allclose(_get(s, "x"), [[0, 0.25, 0.5, 0.75, 1]])
    assert _get(s, "y").shape == (1, 100)


def test_size_forms():
    s = _run("A = zeros(2, 3); s = size(A); r = size(A, 1); c = size(A, 2); t = size(A, 3);")
    assert np.array_equal(_get(s, "s"), [[2, 3]])
    assert _get(s, "r")[0, 0] == 2 and _get(s, "c")[0, 0] == 3 and _get(s, "t")[0, 0] == 1


def test_size_multi_return():
    s = _run("[m, n] = size(ones(4, 5));")
    assert _get(s, "m")[0, 0] == 4 and _get(s, "n")[0, 0] == 5


def test_numel_length():
    s = _run("A = ones(2, 7); k = numel(A); L = length(A); e = length(zeros(0, 3));")
    assert _get(s, "k")[0, 0] == 14
    assert _get(s, "L")[0, 0] == 7
    assert _get(s, "e")[0, 0] == 0


def test_which_reports_builtin():
    s = Session.create_default()
    assert s.functions.which("zeros") == "builtin/zeros"


def test_bad_args_raise_eval_error():
    s = Session.create_default()
    with pytest.raises(EvalError, match="zeros"):
        ReplSession(s).run_line("zeros(1.5)")


def test_variable_shadows_builtin():
    s = _run("zeros = [7 8]; v = zeros(2);")
    assert _get(s, "v")[0, 0] == 8
