"""Arithmetic on logical promotes to double (Issue #239)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _val(code: str):
    s = Session.create_default()
    ReplSession(s).run_line(code + ";")
    v = np.asarray(s.workspace.get("x").backend_buffer())
    return v.dtype, v.reshape(-1, order="F").tolist()


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("true + true", [2.0]),
        ("true - true - true", [-1.0]),
        ("[true true] * [true; true]", [2.0]),
        ("[true false] .* [true true]", [1.0, 0.0]),
        ("true(2) + 1", [2.0, 2.0, 2.0, 2.0]),
        ("true / 2", [0.5]),
        ("-true", [-1.0]),
        ("([1 2] > 1) + ([1 2] > 0)", [1.0, 2.0]),
    ],
)
def test_logical_arithmetic_is_double(expr, expected):
    dtype, vals = _val("x = " + expr)
    assert dtype == np.float64
    assert vals == expected
