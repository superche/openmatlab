"""Linear solve (Epic #496): mldivide/mrdivide, least squares, warnings, inv/det/rank/pinv."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime import warnings as mw
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture(autouse=True)
def _reset_warnings():
    mw.set_enabled(True)
    mw.set_last("")
    yield
    mw.set_enabled(True)
    mw.set_last("")


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def test_square_solve_and_mrdivide():
    ws = _ws("A = [4 -2 1; 3 6 -4; 2 1 8]; b = [12; -25; 32]; x = A \\ b;"
             " y = [1 2; 3 4] / [1 2; 3 4]; z = [1 2 3] / A;")
    np.testing.assert_allclose(_v(ws, "x").ravel(), np.linalg.solve(_v(ws, "A"), _v(ws, "b")).ravel())
    np.testing.assert_allclose(_v(ws, "A") @ _v(ws, "x"), _v(ws, "b"), atol=1e-12)
    np.testing.assert_allclose(_v(ws, "y"), np.eye(2), atol=1e-15)
    np.testing.assert_allclose(_v(ws, "z") @ _v(ws, "A"), [[1, 2, 3]], atol=1e-12)
    assert mw.last() == ""


def test_scalar_cases_and_elementwise_left_divide():
    ws = _ws("a = 2 \\ [4 6]; b = [4 6] / 2; c = [2 4] .\\ [4 4]; d = 1 / 0;")
    assert _v(ws, "a").tolist() == [[2, 3]]
    assert _v(ws, "b").tolist() == [[2, 3]]
    assert _v(ws, "c").tolist() == [[2, 1]]
    assert np.isinf(_v(ws, "d")).all()


def test_overdetermined_least_squares():
    ws = _ws("A = [1 1; 1 2; 1 3]; b = [1; 2; 2]; x = A \\ b;")
    np.testing.assert_allclose(_v(ws, "x").ravel(), [2 / 3, 0.5], atol=1e-14)


def test_underdetermined_basic_solution():
    ws = _ws("x = [1 2 3] \\ 6;")
    np.testing.assert_allclose(_v(ws, "x").ravel(), [0, 0, 2], atol=1e-14)


def test_rank_deficient_warning_and_basic_solution(capsys):
    ws = _ws("x = [1 1; 1 1; 1 1] \\ [1; 2; 3];")
    np.testing.assert_allclose(_v(ws, "x").ravel(), [2, 0], atol=1e-14)
    assert mw.last().startswith("Rank deficient, rank = 1, tol = ")
    assert "Warning: Rank deficient, rank = 1" in capsys.readouterr().err


def test_singular_and_badly_scaled_warnings():
    _ws("x = [1 2; 2 4] \\ [1; 2];")
    assert mw.last() == "Matrix is singular to working precision."
    _ws("x = [1 1e-17; 0 1e-17] \\ [1; 1];")
    assert mw.last().startswith("Matrix is close to singular or badly scaled. Results may be inaccurate. RCOND = ")


def test_dimension_and_type_errors():
    for code in ("x = [1 2] \\ [1; 2];", "x = 1 / [1 2];", "x = int8([2 0; 0 4]) \\ [2; 4];",
                 "x = ones(2,2,2) \\ [1; 1];"):
        with pytest.raises(EvalError):
            _ws(code)
    with pytest.raises(EvalError, match="Matrix dimensions must agree"):
        _ws("x = [1 2] \\ [1; 2];")


def test_complex_single_sparse():
    ws = _ws("x = [1i 0; 0 2] \\ [1; 1]; s = single([2 0; 0 4]) \\ [2; 4]; c = class(s);"
             " S = sparse([2 0; 0 4]); y = S \\ [2; 4];")
    np.testing.assert_allclose(_v(ws, "x").ravel(), [-1j, 0.5])
    assert ws.get("c").text == "single"
    assert _v(ws, "y").ravel().tolist() == [1, 1]


def test_inv_det_rank_pinv():
    ws = _ws("I = inv([1 2; 3 4]); d = det([1 2; 3 4]); r = rank([1 2; 2 4]); r3 = rank([8 1 6; 3 5 7; 4 9 2]);"
             " P = pinv([1 2; 2 4]); Q = pinv([1 2; 3 4; 5 6]); rt = rank([1 0; 0 1e-3], 1e-2);"
             " d0 = det([]);")
    np.testing.assert_allclose(_v(ws, "I"), [[-2, 1], [1.5, -0.5]])
    np.testing.assert_allclose(_v(ws, "d"), -2)
    assert _v(ws, "r").item() == 1 and _v(ws, "r3").item() == 3 and _v(ws, "rt").item() == 1
    np.testing.assert_allclose(_v(ws, "P"), [[0.04, 0.08], [0.08, 0.16]], atol=1e-15)
    np.testing.assert_allclose(_v(ws, "Q"), np.linalg.pinv(np.array([[1, 2], [3, 4], [5, 6]])))
    assert _v(ws, "d0").item() == 1


def test_inv_singular_is_inf_with_warning():
    ws = _ws("X = inv([1 2; 2 4]);")
    assert np.isinf(_v(ws, "X")).all()
    assert mw.last() == "Matrix is singular to working precision."
    with pytest.raises(EvalError, match="square"):
        _ws("X = inv([1 2 3]);")


def test_warning_lastwarn_and_off(capsys):
    ws = _ws("warning('value %d', 3); w = lastwarn; warning('off', 'all'); warning('quiet');"
             " w2 = lastwarn; warning('on', 'all');")
    assert "Warning: value 3" in capsys.readouterr().err
    assert ws.get("w").text == "value 3"
    assert ws.get("w2").text == "quiet"
