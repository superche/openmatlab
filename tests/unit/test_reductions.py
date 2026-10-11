"""sum/prod/mean/min/max (Issue #45)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code: str) -> Session:
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _g(s: Session, n: str) -> np.ndarray:
    return np.asarray(s.workspace.get(n).backend_buffer())


def test_sum_row_and_column_vectors_to_scalar():
    s = _ws("a = sum([1 2 3]); b = sum([1; 2; 3]);")
    assert _g(s, "a").shape == (1, 1) and _g(s, "a")[0, 0] == 6
    assert _g(s, "b")[0, 0] == 6


def test_sum_matrix_columns_and_dim():
    s = _ws("A = [1 2; 3 4]; c = sum(A); r = sum(A, 2); k = sum(A, 3);")
    assert np.array_equal(_g(s, "c"), [[4, 6]])
    assert np.array_equal(_g(s, "r"), [[3], [7]])
    assert np.array_equal(_g(s, "k"), [[1, 2], [3, 4]])


def test_prod_and_mean():
    s = _ws("p = prod([1 2 3 4]); m = mean([1 2; 3 4]); m2 = mean([2 4 6]);")
    assert _g(s, "p")[0, 0] == 24
    assert np.array_equal(_g(s, "m"), [[2, 3]])
    assert _g(s, "m2")[0, 0] == 4


def test_empty_special_cases():
    s = _ws("z = sum([]); o = prod([]); n = mean([]);")
    assert _g(s, "z")[0, 0] == 0
    assert _g(s, "o")[0, 0] == 1
    assert math.isnan(_g(s, "n")[0, 0])


def test_max_min_vector_with_index():
    s = _ws("[m, i] = max([3 9 2 9]); [lo, j] = min([3 9 2 9]);")
    assert _g(s, "m")[0, 0] == 9 and _g(s, "i")[0, 0] == 2  # first occurrence, 1-based
    assert _g(s, "lo")[0, 0] == 2 and _g(s, "j")[0, 0] == 3


def test_max_matrix_columns_and_dim_form():
    s = _ws("A = [1 5; 7 2]; c = max(A); [r, k] = max(A, [], 2);")
    assert np.array_equal(_g(s, "c"), [[7, 5]])
    assert np.array_equal(_g(s, "r"), [[5], [7]])
    assert np.array_equal(_g(s, "k"), [[2], [1]])


def test_max_two_arg_elementwise_and_scalar_broadcast():
    s = _ws("e = max([1 5 3], [4 2 6]); f = min([1 5 3], 2);")
    assert np.array_equal(_g(s, "e"), [[4, 5, 6]])
    assert np.array_equal(_g(s, "f"), [[1, 2, 2]])


def test_reduction_bad_args():
    s = Session.create_default()
    with pytest.raises(EvalError):
        ReplSession(s).run_line("max([1 2], [1 2 3])")
    with pytest.raises(EvalError):
        ReplSession(s).run_line("sum([1 2], 0)")


def test_max_min_skip_nan_by_default():
    """MATLAB default: omitnan. Do not weaken."""
    s = _ws("v = max([1 nan() 3]); w = min([1 nan() 3]);")
    assert _g(s, "v")[0, 0] == 3
    assert _g(s, "w")[0, 0] == 1


def test_max_all_nan_returns_nan_and_index_one():
    s = _ws("[m, i] = max([nan() nan()]); [n, j] = min([nan(); nan()]);")
    assert math.isnan(_g(s, "m")[0, 0]) and _g(s, "i")[0, 0] == 1
    assert math.isnan(_g(s, "n")[0, 0]) and _g(s, "j")[0, 0] == 1


def test_max_index_skips_nan_first_occurrence():
    s = _ws("[m, i] = max([nan() 2 5 nan() 5]);")
    assert _g(s, "m")[0, 0] == 5 and _g(s, "i")[0, 0] == 3


def test_max_matrix_columns_skip_nan():
    s = _ws("A = [1 nan(); nan() 4]; c = max(A); [r, k] = max(A, [], 2);")
    assert np.array_equal(_g(s, "c"), [[1, 4]])
    assert np.array_equal(_g(s, "r"), [[1], [4]])
    assert np.array_equal(_g(s, "k"), [[1], [2]])


def test_max_min_two_arg_prefer_non_nan():
    s = _ws(
        "e = max([1 nan() 3], [nan() 2 nan()]); "
        "f = min([1 nan()], [nan() 2]); "
        "g = max(nan(), nan());"
    )
    assert np.array_equal(_g(s, "e"), [[1, 2, 3]])
    assert np.array_equal(_g(s, "f"), [[1, 2]])
    assert math.isnan(_g(s, "g")[0, 0])


def test_nan_constructor():
    s = _ws("a = nan(); b = NaN(2, 3);")
    assert math.isnan(_g(s, "a")[0, 0])
    assert _g(s, "b").shape == (2, 3) and np.isnan(_g(s, "b")).all()

