import pytest

from openmatlab.ast_nodes import Assign, BinOp, ExprStmt, Name, Number, UnaryOp
from openmatlab.parser import ParseError, parse


def test_number_expr():
    stmts = parse("42")
    assert len(stmts) == 1
    assert isinstance(stmts[0], ExprStmt)
    assert stmts[0].expr == Number(42.0)


def test_assignment():
    stmts = parse("a = 1 + 2")
    assert isinstance(stmts[0], Assign)
    assert stmts[0].name == "a"
    assert isinstance(stmts[0].value, BinOp)


def test_precedence_mul_over_add():
    stmts = parse("1 + 2 * 3")
    expr = stmts[0].expr
    assert isinstance(expr, BinOp)
    assert expr.op == "+"
    assert isinstance(expr.right, BinOp)
    assert expr.right.op == "*"


def test_parens():
    stmts = parse("(1 + 2) * 3")
    expr = stmts[0].expr
    assert isinstance(expr, BinOp)
    assert expr.op == "*"
    assert isinstance(expr.left, BinOp)


def test_unary_minus():
    stmts = parse("-x")
    expr = stmts[0].expr
    assert isinstance(expr, UnaryOp)
    assert expr.op == "-"
    assert isinstance(expr.operand, Name)


def test_multiple_statements():
    stmts = parse("a = 1; b = 2\nc = a + b")
    assert len(stmts) == 3
    assert all(isinstance(s, Assign) for s in stmts)


def test_parse_error():
    with pytest.raises(ParseError):
        parse("(")
