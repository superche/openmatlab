import pytest

from openmatlab.lang.lexer import LexerError, tokenize
from openmatlab.lang.tokens import TokenType

pytestmark = pytest.mark.unit


def types(src: str):
    return [t.type for t in tokenize(src) if t.type != TokenType.EOF]


def test_matrix_and_dot_ops():
    assert TokenType.LBRACKET in types("[1 2; 3 4]")
    assert TokenType.DOT_STAR in types("a .* b")
    assert TokenType.DOT_SLASH in types("a ./ b")
    assert TokenType.DOT_HAT in types("a .^ b")
    assert TokenType.STAR in types("a * b")


def test_colon_transpose_comma():
    assert TokenType.COLON in types("1:10")
    assert TokenType.TRANSPOSE in types("A'")
    assert TokenType.CTC_TRANSPOSE in types("A.'")
    assert TokenType.COMMA in types("f(1, 2)")


def test_newline_inside_matrix_becomes_row_sep():
    toks = types("[\n 1 2\n 3 4\n]")
    assert TokenType.SEMICOLON in toks


def test_comment_and_at_handle():
    assert types("1 % c\n2") == [TokenType.NUMBER, TokenType.NEWLINE, TokenType.NUMBER]
    # EPIC-023 / #276: @ is function-handle introducer (was LexerError)
    assert types("@numel") == [TokenType.AT, TokenType.IDENT]
