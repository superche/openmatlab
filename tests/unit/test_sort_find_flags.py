"""sort descend + find first/last (Issue #189)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return lambda n: np.asarray(s.workspace.get(n).backend_buffer())


def test_sort_descend_and_indices():
    g = _ws("[b, i] = sort([3 1 2], 'descend'); a = sort([3 1 2], 'ascend');")
    assert g("b").tolist() == [[3, 2, 1]]
    assert g("i").tolist() == [[1, 3, 2]]
    assert g("a").tolist() == [[1, 2, 3]]


def test_sort_dim_descend_and_stable_ties():
    g = _ws("B = sort([1 4; 3 2], 2, 'descend'); [t, j] = sort([2 1 2], 'descend');")
    assert g("B").tolist() == [[4, 1], [3, 2]]
    assert g("j").tolist() == [[1, 3, 2]]


def test_find_first_last_k():
    g = _ws('f = find([0 1 1 0 1], 2, "last"); h = find([0 1 1 0 1], 2, "first");')
    assert g("f").tolist() == [[3, 5]]
    assert g("h").tolist() == [[2, 3]]


def test_find_matrix_last_is_column():
    g = _ws("k = find([0 2; 3 4], 2, 'last');")
    assert g("k").tolist() == [[3], [4]]


def test_bad_flags_error():
    s = Session.create_default()
    with pytest.raises(EvalError):
        ReplSession(s).run_line("x = sort([1 2], 'sideways');")
    with pytest.raises(EvalError):
        ReplSession(s).run_line("x = find([1 2], 1, 'middle');")
