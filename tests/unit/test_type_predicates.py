"""class / is* predicates / any / all builtins (Issue #414)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _x(expr: str):
    s = Session.create_default()
    ReplSession(s).run_line(f"x = {expr};")
    return s.workspace.get("x")


@pytest.mark.parametrize(
    "expr, cls",
    [("1", "double"), ("true", "logical"), ("[1 2] > 1", "logical"),
     ("'a'", "char"), ("{}", "cell"), ("@sin", "function_handle")],
)
def test_class(expr, cls):
    v = _x(f"class({expr})")
    assert isinstance(v, CharValue) and v.text == cls


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("islogical(true)", True), ("islogical(1)", False),
        ("isnumeric(1)", True), ("isnumeric(true)", False), ("isnumeric('a')", False),
        ("ischar('a')", True), ("ischar(1)", False),
        ("iscell({1})", True), ("iscell(1)", False),
        ("isempty([])", True), ("isempty(zeros(0, 3))", True), ("isempty('')", True),
        ("isempty({})", True), ("isempty(1)", False), ("isempty('a')", False),
        ("any([])", False), ("all([])", True),
        ("all([1 0; 1 1], 'all')", False), ("any(NaN)", True),
    ],
)
def test_scalar_logical_results(expr, expected):
    v = _x(expr)
    buf = np.asarray(v.backend_buffer())
    assert buf.dtype == np.bool_ and buf.shape == (1, 1)
    assert bool(buf[0, 0]) is expected


def test_any_all_columnwise_and_dim():
    b = lambda e: np.asarray(_x(e).backend_buffer()).tolist()
    assert b("any([0 1; 0 0])") == [[False, True]]
    assert b("all([1 1; 0 1])") == [[False, True]]
    assert b("any([0 0 1])") == [[True]]  # vector → scalar
    assert b("any([0 0; 0 1], 2)") == [[False], [True]]
