import pytest

from openmatlab.lang.ast_nodes import (
    Assign,
    BinOp,
    ColonExpr,
    ExprStmt,
    IndexExpr,
    MatrixLiteral,
    Name,
    NumberLiteral,
    TransposeExpr,
)
from openmatlab.lang.parser import ParseError, parse

pytestmark = pytest.mark.unit


def test_matrix_literal_2x2():
    stmts = parse("[1 2; 3 4]")
    assert isinstance(stmts[0], ExprStmt)
    m = stmts[0].expr
    assert isinstance(m, MatrixLiteral)
    assert len(m.rows) == 2
    assert len(m.rows[0]) == 2
    assert m.rows[0][0] == NumberLiteral(1.0)
    assert m.rows[1][1] == NumberLiteral(4.0)


def test_star_vs_dot_star():
    a = parse("A * B")[0].expr
    b = parse("A .* B")[0].expr
    assert isinstance(a, BinOp) and a.op == "*"
    assert isinstance(b, BinOp) and b.op == ".*"


def test_colon_and_step():
    c = parse("1:10")[0].expr
    assert isinstance(c, ColonExpr)
    assert c.step is None
    c2 = parse("1:2:9")[0].expr
    assert isinstance(c2, ColonExpr)
    assert isinstance(c2.step, NumberLiteral)


def test_transpose_and_index():
    t = parse("A'")[0].expr
    assert isinstance(t, TransposeExpr) and t.conjugate is True
    t2 = parse("A.'")[0].expr
    assert isinstance(t2, TransposeExpr) and t2.conjugate is False
    ix = parse("A(1, 2)")[0].expr
    assert isinstance(ix, IndexExpr)
    assert isinstance(ix.target, Name)
    assert len(ix.indices) == 2


def test_assign_suppress():
    s = parse("a = [1 2];")[0]
    assert isinstance(s, Assign)
    assert s.suppress is True
    s2 = parse("1 + 2")[0]
    assert isinstance(s2, ExprStmt)
    assert s2.suppress is False


def test_precedence_mul_over_add_and_power():
    e = parse("1 + 2 * 3")[0].expr
    assert isinstance(e, BinOp) and e.op == "+"
    assert isinstance(e.right, BinOp) and e.right.op == "*"


def test_matrix_add_single_element():
    """[1+2] is one element, not juxtaposition of 1 and +2."""
    m = parse("[1+2]")[0].expr
    assert isinstance(m, MatrixLiteral)
    assert len(m.rows) == 1 and len(m.rows[0]) == 1
    assert isinstance(m.rows[0][0], BinOp)


def test_parse_error():
    with pytest.raises(ParseError):
        parse("(")
