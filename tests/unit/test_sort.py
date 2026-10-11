"""sort builtin (Issue #89)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code: str) -> Session:
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _g(s: Session, n: str) -> np.ndarray:
    return np.asarray(s.workspace.get(n).backend_buffer())


def test_sort_vector_and_index():
    s = _ws("[B, I] = sort([3 1 2]);")
    assert np.array_equal(_g(s, "B"), [[1, 2, 3]])
    assert np.array_equal(_g(s, "I"), [[2, 3, 1]])


def test_sort_matrix_columns_and_dim():
    s = _ws("A = [3 1; 2 4]; C = sort(A); R = sort(A, 2);")
    assert np.array_equal(_g(s, "C"), [[2, 1], [3, 4]])
    assert np.array_equal(_g(s, "R"), [[1, 3], [2, 4]])


def test_sort_stable_ties():
    s = _ws("[B, I] = sort([2 2 1]);")
    assert np.array_equal(_g(s, "B"), [[1, 2, 2]])
    assert list(_g(s, "I").reshape(-1)) == [3, 1, 2]
