"""Language addpath / which (Issue #20)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import StringLiteral
from openmatlab.lang.lexer import tokenize
from openmatlab.lang.parser import parse
from openmatlab.lang.tokens import TokenType
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_lex_double_quoted_string():
    toks = [t for t in tokenize('"hello"') if t.type != TokenType.EOF]
    assert toks[0].type == TokenType.STRING
    assert toks[0].value == "hello"


def test_parse_string_literal():
    stmts = parse('s = "abc"')
    assert isinstance(stmts[0].value, StringLiteral)
    assert stmts[0].value.value == "abc"


def test_addpath_which_and_call(tmp_path: Path):
    (tmp_path / "add2.m").write_text(
        "function y = add2(a, b)\ny = a + b;\nend\n"
    )
    s = Session.create_default()
    ReplSession(s).run_line(f'addpath("{tmp_path}")')
    ReplSession(s).run_line('which("add2")')
    w = s.workspace.get("ans")
    assert isinstance(w, CharValue)
    assert w.text.endswith("add2.m")
    ReplSession(s).run_line("r = add2(7, 8);")
    assert float(s.workspace.get("r").backend_buffer().reshape(-1)[0]) == 15.0


def test_which_missing():
    s = Session.create_default()
    ReplSession(s).run_line('which("no_such_fn")')
    w = s.workspace.get("ans")
    assert isinstance(w, CharValue)
    assert w.text == ""
