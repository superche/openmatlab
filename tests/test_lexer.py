import pytest

from openmatlab.lexer import LexerError, TokenType, tokenize


def types(source: str):
    return [t.type for t in tokenize(source) if t.type != TokenType.EOF]


def values(source: str):
    return [(t.type, t.value) for t in tokenize(source) if t.type != TokenType.EOF]


def test_numbers():
    assert types("42") == [TokenType.NUMBER]
    assert values("3.14") == [(TokenType.NUMBER, "3.14")]
    assert values("1e3") == [(TokenType.NUMBER, "1e3")]
    assert values(".5") == [(TokenType.NUMBER, ".5")]


def test_identifiers_and_ops():
    assert types("a = b + c") == [
        TokenType.IDENT,
        TokenType.ASSIGN,
        TokenType.IDENT,
        TokenType.PLUS,
        TokenType.IDENT,
    ]


def test_parens_mul_div():
    assert types("(1*2)/3") == [
        TokenType.LPAREN,
        TokenType.NUMBER,
        TokenType.STAR,
        TokenType.NUMBER,
        TokenType.RPAREN,
        TokenType.SLASH,
        TokenType.NUMBER,
    ]


def test_semicolon_and_newline():
    toks = tokenize("1;2\n3")
    types_ = [t.type for t in toks if t.type != TokenType.EOF]
    assert TokenType.SEMICOLON in types_
    assert TokenType.NEWLINE in types_


def test_comment_skipped():
    assert types("1 % comment\n2") == [
        TokenType.NUMBER,
        TokenType.NEWLINE,
        TokenType.NUMBER,
    ]


def test_unexpected_char():
    with pytest.raises(LexerError):
        tokenize("@")
