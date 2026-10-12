"""size / numel / length for cell, char and handle values (Issue #423)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _v(expr: str):
    s = Session.create_default()
    ReplSession(s).run_line(f"x = {expr};")
    return np.asarray(s.workspace.get("x").backend_buffer()).reshape(-1).tolist()


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("size({1, 2})", [1, 2]), ("size({1; 2; 3})", [3, 1]), ("size({})", [0, 0]),
        ("size({1, 2}, 2)", [2]), ("numel({1, 2, 3})", [3]), ("length({1; 2; 3})", [3]),
        ("size('abc')", [1, 3]), ("size('')", [0, 0]), ("numel('abc')", [3]),
        ("length('')", [0]), ("size(@sin)", [1, 1]), ("numel(@sin)", [1]),
        ("size(zeros(0, 3))", [0, 3]), ("length(zeros(0, 3))", [0]),
    ],
)
def test_dimensions_of_any_value(expr, expected):
    assert _v(expr) == expected


def test_multi_output_size_of_cell():
    s = Session.create_default()
    ReplSession(s).run_line("[r, k] = size({1; 2; 3});")
    get = lambda n: np.asarray(s.workspace.get(n).backend_buffer()).reshape(-1).tolist()
    assert (get("r"), get("k")) == ([3], [1])
