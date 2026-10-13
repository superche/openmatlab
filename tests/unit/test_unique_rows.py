"""unique(A,'rows') / issorted(A,'rows') (Issue #270)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return lambda n: np.asarray(s.workspace.get(n).backend_buffer()).tolist()


def test_unique_rows_sorted_with_indices():
    get = _ws("A = [3 1; 1 2; 3 1; 1 2; 0 5]; [C, ia, ic] = unique(A, 'rows');")
    assert get("C") == [[0, 5], [1, 2], [3, 1]]
    assert get("ia") == [[5], [2], [1]]  # first occurrence
    assert get("ic") == [[3], [2], [3], [2], [1]]


@pytest.mark.parametrize(
    "code, expected",
    [
        ("x = issorted([1 2; 1 3; 2 0], 'rows');", True),
        ("x = issorted([1 3; 1 2], 'rows');", False),
        ("x = issorted([2 0; 1 3], 'rows', 'descend');", True),
        ("x = issorted([1 1; 1 1], 'rows');", True),
    ],
)
def test_issorted_rows(code, expected):
    assert _ws(code)("x") == [[expected]]


def test_unique_unknown_option_errors():
    # Changed with user approval (Epic #535): 'stable' is a valid MATLAB option.
    with pytest.raises(Exception, match="unknown option"):
        _ws("C = unique([1 2], 'bogus');")


def test_unique_stable_keeps_first_occurrence_order():
    get = _ws("C = unique([5 5 3 4], 'stable');")
    assert get("C") == [[5, 3, 4]]
