"""Cell paren delete with logical mask / index vector (Issue #311)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _cell(code: str):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    c = s.workspace.get("c")
    r, k = c.shape
    vals = [float(np.asarray(c.get(i, j).backend_buffer()).reshape(-1)[0]) for j in range(k) for i in range(r)]
    return vals, c.shape


def test_logical_mask_delete_row():
    assert _cell("c = {1, 2, 3}; c(logical([1 0 1])) = [];") == ([2.0], (1, 1))


def test_logical_mask_from_comparison_on_column():
    assert _cell("c = {1; 2; 3}; v = [1 2 3]; c(v > 1) = [];") == ([1.0], (1, 1))
    assert _cell("c = {1; 2; 3; 4}; c(logical([0 1 0 1])) = [];") == ([1.0, 3.0], (2, 1))


def test_index_vector_and_end_delete():
    assert _cell("c = {1, 2, 3, 4}; c([1 3]) = [];") == ([2.0, 4.0], (1, 2))
    assert _cell("c = {1, 2, 3}; c(end) = [];") == ([1.0, 2.0], (1, 2))


def test_all_false_mask_is_noop():
    assert _cell("c = {1, 2}; c(logical([0 0])) = [];") == ([1.0, 2.0], (1, 2))


def test_out_of_range_errors():
    with pytest.raises(Exception, match="exceeds 2"):
        _cell("c = {1, 2}; c(5) = [];")
