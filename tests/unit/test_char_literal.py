"""Single-quote char literals vs transpose (Issue #64)."""

from __future__ import annotations

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import StringLiteral, TransposeExpr
from openmatlab.lang.lexer import LexerError, tokenize
from openmatlab.lang.parser import parse
from openmatlab.lang.tokens import TokenType
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit]


def types(src: str):
    return [t.type for t in tokenize(src) if t.type != TokenType.EOF]


def test_char_vs_transpose_tokens():
    assert types("'hi'") == [TokenType.CHAR]
    assert types("''") == [TokenType.CHAR]
    assert tokenize("'a''b'")[0].value == "a'b"
    assert types("A'") == [TokenType.IDENT, TokenType.TRANSPOSE]
    assert types("A.'") == [TokenType.IDENT, TokenType.CTC_TRANSPOSE]
    assert types("[1 2]'")[-1] == TokenType.TRANSPOSE


def test_unterminated_char():
    with pytest.raises(LexerError, match="Unterminated"):
        tokenize("'oops")


def test_parse_char_and_transpose():
    s = parse("s = 'hello'")[0]
    assert isinstance(s.value, StringLiteral) and s.value.value == "hello"
    t = parse("A'")[0].expr
    assert isinstance(t, TransposeExpr) and t.conjugate is True


def test_eval_char_value():
    s = Session.create_default()
    ReplSession(s).run_line("s = 'hi'; e = ''; q = 'a''b';")
    assert isinstance(s.workspace.get("s"), CharValue)
    assert s.workspace.get("s").text == "hi"
    assert s.workspace.get("e").text == ""
    assert s.workspace.get("q").text == "a'b"


@pytest.mark.needs_numpy
def test_transpose_still_works_on_matrix():
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2]; B = A';")
    import numpy as np
    assert np.array_equal(
        np.asarray(s.workspace.get("B").backend_buffer()),
        [[1], [2]],
    )


def test_double_quote_unchanged():
    s = Session.create_default()
    ReplSession(s).run_line('s = "xy";')
    assert s.workspace.get("s").text == "xy"
