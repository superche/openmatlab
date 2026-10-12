"""return in .m functions/scripts (Issue #137)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import ReturnStmt
from openmatlab.lang.lexer import tokenize
from openmatlab.lang.parser import parse
from openmatlab.lang.tokens import TokenType
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_token_and_parse():
    assert TokenType.KW_RETURN in [t.type for t in tokenize("return")]
    assert isinstance(parse("return")[0], ReturnStmt)


def test_return_in_function(tmp_path: Path):
    (tmp_path / "early.m").write_text(
        "function y = early(x)\ny = x + 1;\nreturn;\ny = x + 100;\nend\n"
    )
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f'addpath("{tmp_path}");')
    r.run_line("y = early(5);")
    assert float(s.workspace.get("y").backend_buffer().reshape(-1)[0]) == 6


def test_return_in_script(tmp_path: Path):
    f = tmp_path / "setup.m"
    f.write_text("a = 1;\nreturn;\na = 99;\n")
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f'run("{f}");')
    assert float(s.workspace.get("a").backend_buffer().reshape(-1)[0]) == 1


def test_return_toplevel_errors():
    s = Session.create_default()
    with pytest.raises(EvalError, match="return outside"):
        ReplSession(s).run_line("return;")


def test_early_return_with_multiple_outputs(tmp_path: Path):
    """Issue #140: assign outputs, then early `return` (MATLAB pattern)."""
    (tmp_path / "early.m").write_text(
        "function [a, b] = early(x)\na = 1;\nif x > 0\n  b = 2;\n  return\nend\nb = 3;\nend\n"
    )
    s = Session.create_default()
    ReplSession(s).run_line(f'addpath("{tmp_path}"); [p, q] = early(1); [r, t] = early(-1);')
    got = [float(s.workspace.get(n).backend_buffer().reshape(-1)[0]) for n in ("p", "q", "r", "t")]
    assert got == [1.0, 2.0, 1.0, 3.0]
