"""Gherkin for matrix lexer/parser (Issue #3)."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from openmatlab.lang.ast_nodes import BinOp, ExprStmt, MatrixLiteral
from openmatlab.lang.parser import parse

pytestmark = [pytest.mark.bdd, pytest.mark.unit]

scenarios("../../features/matrix_parser.feature")


@when(parsers.parse('I parse "{source}"'), target_fixture="stmts")
def do_parse(source: str):
    return parse(source)


@then("the statement expression is a matrix with 2 rows")
def matrix_two_rows(stmts):
    expr = stmts[0].expr
    assert isinstance(stmts[0], ExprStmt)
    assert isinstance(expr, MatrixLiteral)
    assert len(expr.rows) == 2


@then(parsers.parse('the binary operator is "{op}"'))
def binop_is(stmts, op: str):
    expr = stmts[0].expr
    assert isinstance(expr, BinOp)
    assert expr.op == op
