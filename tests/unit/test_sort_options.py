"""sort name-value options ComparisonMethod / MissingPlacement (Issue #197)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _x(expr):
    s = Session.create_default()
    ReplSession(s).run_line(f"x = {expr};")
    return ["NaN" if math.isnan(v) else v for v in np.asarray(s.workspace.get("x").backend_buffer()).reshape(-1)]


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("sort([3 NaN 1 2])", [1, 2, 3, "NaN"]),  # auto: NaN last ascending
        ("sort([3 NaN 1 2], 'descend')", ["NaN", 3, 2, 1]),  # auto: NaN first descending
        ("sort([3 NaN 1], 'MissingPlacement', 'first')", ["NaN", 1, 3]),
        ("sort([3 NaN 1], 'descend', 'MissingPlacement', 'last')", [3, 1, "NaN"]),
        ("sort([-3 2 -1], 'ComparisonMethod', 'abs')", [-1, 2, -3]),
        ("sort([-3 2 -1], 'ComparisonMethod', 'real')", [-3, -1, 2]),
        ("sort([2 -2 1], 'ComparisonMethod', 'abs')", [1, -2, 2]),  # |ties| by value
    ],
)
def test_sort_options(expr, expected):
    assert _x(expr) == expected


def test_bad_option_values():
    for expr in ("sort([1 2], 'MissingPlacement', 'middle')", "sort([1 2], 'ComparisonMethod')"):
        with pytest.raises(Exception):
            _x(expr)
