"""find builtin (Issue #90)."""

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


def test_find_linear_column_major():
    s = _ws("A = [0 2; 3 0]; i = find(A);")
    assert list(_g(s, "i").reshape(-1)) == [2, 3]


def test_find_k_limit():
    s = _ws("A = [0 2; 3 0]; k = find(A, 1);")
    assert list(_g(s, "k").reshape(-1)) == [2]


def test_find_subscripts_and_values():
    s = _ws("A = [0 2; 3 0]; [r, c, v] = find(A);")
    assert list(_g(s, "r").reshape(-1)) == [2, 1]
    assert list(_g(s, "c").reshape(-1)) == [1, 2]
    assert list(_g(s, "v").reshape(-1)) == [3, 2]


def test_find_empty():
    s = _ws("i = find([0 0]); j = find([]);")
    assert _g(s, "i").shape[0] == 0
    assert _g(s, "j").shape[0] == 0


def test_find_skips_nan():
    s = _ws("i = find([nan() 0 5]);")
    assert list(_g(s, "i").reshape(-1)) == [3]
