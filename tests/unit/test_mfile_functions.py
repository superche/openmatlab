"""Parse and evaluate .m functions (Issue #6)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import FunctionDef
from openmatlab.lang.lexer import tokenize
from openmatlab.lang.parser import parse
from openmatlab.lang.tokens import TokenType
from openmatlab.numerics.numpy_backend import NumPyArrayBackend
from openmatlab.runtime.evaluator import EvalError, Evaluator
from openmatlab.runtime.functions import FunctionResolver, parse_mfile
from openmatlab.runtime.session import Session
from openmatlab.runtime.workspace import Workspace

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_lexer_keywords():
    types = [t.type for t in tokenize("function y = f(x)\nend") if t.type != TokenType.EOF]
    assert TokenType.KW_FUNCTION in types
    assert TokenType.KW_END in types


def test_parse_function_def():
    stmts = parse("function y = add2(a, b)\ny = a + b;\nend")
    assert len(stmts) == 1
    fn = stmts[0]
    assert isinstance(fn, FunctionDef)
    assert fn.name == "add2"
    assert list(fn.inputs) == ["a", "b"]
    assert list(fn.outputs) == ["y"]
    assert len(fn.body) == 1


def test_parse_mfile_and_call(tmp_path: Path):
    f = tmp_path / "add2.m"
    f.write_text("function y = add2(a, b)\ny = a + b;\nend\n")
    defn = parse_mfile(f)
    assert defn.name == "add2"
    path = __import__("openmatlab.libs.path", fromlist=["ToolboxPath"]).ToolboxPath()
    path.addpath(tmp_path)
    res = FunctionResolver(path=path)
    be = NumPyArrayBackend()
    res.bind_runtime(be)
    fn = res.resolve("add2")
    a = be.from_scalar(2.0)
    b = be.from_scalar(3.0)
    out = fn([a, b], nargout=1)[0]
    assert float(out.backend_buffer().reshape(-1)[0]) == 5.0


def test_eval_call_from_path(tmp_path: Path):
    (tmp_path / "times3.m").write_text(
        "function y = times3(x)\ny = x * 3;\nend\n"
        # wait - x * 3: 3 is scalar 1x1, x is 1x1, matmul works for 1x1
    )
    s = Session.create_default()
    s.path.addpath(tmp_path)
    ReplSession(s).run_line("r = times3(4);")
    assert float(s.workspace.get("r").backend_buffer().reshape(-1)[0]) == 12.0


def test_multi_output_and_matrix(tmp_path: Path):
    (tmp_path / "swap.m").write_text(
        "function [a, b] = swap(x, y)\na = y;\nb = x;\nend\n"
    )
    # only nargout=1 used by evaluator MVP — first output
    s = Session.create_default()
    s.path.addpath(tmp_path)
    ReplSession(s).run_line("z = swap(1, 2);")
    assert float(s.workspace.get("z").backend_buffer().reshape(-1)[0]) == 2.0


def test_undefined_function(tmp_path: Path):
    s = Session.create_default()
    s.path.addpath(tmp_path)
    with pytest.raises(EvalError, match="Undefined"):
        ReplSession(s).run_line("missing(1)")
