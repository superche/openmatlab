"""Logical operators ~ & | && || and not/and/or/xor (Issue #413)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import BinOp, UnaryOp
from openmatlab.lang.parser import parse
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _x(expr: str):
    s = Session.create_default()
    ReplSession(s).run_line(f"x = {expr};")
    v = np.asarray(s.workspace.get("x").backend_buffer())
    return v.dtype, v.reshape(-1, order="F").tolist()


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("~true", [False]),
        ("~[1 0 2]", [False, True, False]),
        ("[1 0 1] & [1 1 0]", [True, False, False]),
        ("[1 0 1] | [0 0 1]", [True, False, True]),
        ("1 && 0", [False]),
        ("0 || 2", [True]),
        ("not([1 0])", [False, True]),
        ("and(1, [0 1])", [False, True]),
        ("or(0, 0)", [False]),
        ("xor([1 1], [0 1])", [True, False]),
    ],
)
def test_results_are_logical(expr, expected):
    dtype, vals = _x(expr)
    assert dtype == np.bool_
    assert vals == expected


def test_precedence_matches_matlab():
    # || < && < | < & < relational < ... < unary ~ (above +, below ^)
    (stmt,) = parse("a || b && c")
    assert stmt.expr.op == "||" and stmt.expr.right.op == "&&"
    (stmt,) = parse("a | b & c")
    assert stmt.expr.op == "|" and stmt.expr.right.op == "&"
    (stmt,) = parse("a < b & c > d")
    assert stmt.expr.op == "&"
    (stmt,) = parse("~a + 1")
    assert isinstance(stmt.expr, BinOp) and isinstance(stmt.expr.left, UnaryOp)
    assert _x("~0 + 1")[1] == [2.0]
    assert _x("1 | 0 & 0")[1] == [True]
    assert _x("1 ~= 2")[1] == [True]


def test_short_circuit_skips_right_operand():
    assert _x("0 && undefined_name")[1] == [False]
    assert _x("1 || undefined_name")[1] == [True]


def test_short_circuit_requires_scalars():
    with pytest.raises(EvalError, match="logical scalar"):
        _x("[1 2] && 1")


def test_nan_to_logical_errors():
    with pytest.raises(Exception, match="NaN"):
        _x("1 & NaN")


def test_unary_not_in_matrix_literal_separates_elements():
    assert _x("[1 ~0 ~1]")[1] == [1.0, 1.0, 0.0]
    assert _x("[1 ~= 0]")[1] == [True]
