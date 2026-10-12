"""Cell paren assign broadcast / size rules (Issue #291) — same rules as arrays (#164)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _c(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    c = s.workspace.get("c")
    r, k = c.shape
    val = lambda v: float(np.asarray(v.backend_buffer()).reshape(-1)[0]) if v.numel() else None
    return [[val(c.get(i, j)) for j in range(k)] for i in range(r)]


def test_scalar_cell_broadcasts():
    assert _c("c = cell(1, 3); c(1:2) = {5};") == [[5, 5, None]]
    assert _c("c = cell(2, 2); c(:, 1) = {7};") == [[7, None], [7, None]]


def test_matching_shapes_assign():
    assert _c("c = cell(2, 2); c(1:2, 1:2) = {1, 2; 3, 4};") == [[1, 2], [3, 4]]
    assert _c("c = cell(2, 2); c(1:2, 1) = {1, 2};") == [[1, None], [2, None]]  # vector orientation free


def test_mismatches_error():
    with pytest.raises(EvalError, match="numel"):
        _c("c = cell(1, 3); c(1:2) = {5, 6, 7};")
    with pytest.raises(EvalError, match="left side is 2-by-2 and the size of the right side is 1-by-4"):
        _c("c = cell(2, 2); c(1:2, 1:2) = {1, 2, 3, 4};")
