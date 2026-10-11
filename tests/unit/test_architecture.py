"""Smoke tests: seams import and Session wires without float-eval guts."""

import pytest

from openmatlab.host.cli import main
from openmatlab.host.display import NullDisplay
from openmatlab.host.plot_surface import StubPlotSurface
from openmatlab.lang.ast_nodes import Assign, MatrixLiteral, NumberLiteral
from openmatlab.lang.tokens import TokenType
from openmatlab.libs.path import ToolboxPath
from openmatlab.runtime.session import Session
from openmatlab.runtime.workspace import Workspace

pytestmark = pytest.mark.unit


def test_matrix_tokens_reserved():
    for name in ("LBRACKET", "DOT_STAR", "COLON", "TRANSPOSE", "KW_FUNCTION"):
        assert hasattr(TokenType, name)


def test_ast_matrix_forms_exist():
    lit = MatrixLiteral(rows=(((NumberLiteral(1.0),),),))
    assert lit.rows
    stmt = Assign(name="A", value=NumberLiteral(1.0), suppress=True)
    assert stmt.suppress is True


def test_workspace_frames():
    ws = Workspace()
    assert ws.depth() == 1
    ws.push()
    assert ws.depth() == 2
    ws.pop()
    assert ws.depth() == 1


def test_session_composition():
    s = Session.create_default()
    assert s.workspace.depth() == 1
    assert s.functions.path is s.path
    assert isinstance(s.display, NullDisplay)
    assert isinstance(s.plots, StubPlotSurface)
    assert isinstance(s.path, ToolboxPath)
    assert s.numerics is None


def test_plot_surface_stub_raises():
    with pytest.raises(NotImplementedError):
        StubPlotSurface().plot()


def test_lexer_parser_minimal_number():
    """Issue #3: lexer/parser are real (no longer stubs)."""
    from openmatlab.lang.ast_nodes import ExprStmt, NumberLiteral
    from openmatlab.lang.lexer import tokenize
    from openmatlab.lang.parser import parse
    from openmatlab.lang.tokens import TokenType

    toks = tokenize("1")
    assert toks[0].type == TokenType.NUMBER
    stmts = parse("1")
    assert isinstance(stmts[0], ExprStmt)
    assert stmts[0].expr == NumberLiteral(1.0)


def test_no_float_dict_evaluator_module():
    """Scalar float-dict evaluator must stay deleted."""
    import importlib.util

    spec = importlib.util.find_spec("openmatlab.evaluator")
    assert spec is None


def test_cli_status(capsys):
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "architecture" in out
    assert "runtime" in out
    assert "docs/QA.md" in out
