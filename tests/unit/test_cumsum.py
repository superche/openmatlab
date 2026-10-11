"""cumsum builtin (Issue #88)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _g(code: str, name: str) -> np.ndarray:
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer())


def test_cumsum_vector_and_matrix():
    assert np.array_equal(_g("y = cumsum([1 2 3 4]);", "y"), [[1, 3, 6, 10]])
    assert np.array_equal(_g("y = cumsum([1; 2; 3]);", "y"), [[1], [3], [6]])
    assert np.array_equal(
        _g("y = cumsum([1 2; 3 4]);", "y"),
        [[1, 2], [4, 6]],
    )


def test_cumsum_dim():
    assert np.array_equal(
        _g("y = cumsum([1 2; 3 4], 2);", "y"),
        [[1, 3], [3, 7]],
    )


def test_which_cumsum():
    s = Session.create_default()
    assert s.functions.which("cumsum") == "builtin/cumsum"
