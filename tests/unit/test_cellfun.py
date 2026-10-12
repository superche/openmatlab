"""cellfun + @function_handle (Issue #276)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import FuncHandleExpr
from openmatlab.lang.parser import parse
from openmatlab.runtime.function_handle import FunctionHandleValue
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_parse_at_handle():
    stmt = parse("fh = @numel;")[0]
    assert isinstance(stmt.value, FuncHandleExpr)
    assert stmt.value.name == "numel"


def test_cellfun_c10():
    s = Session.create_default()
    ReplSession(s).run_line("c = {[1 2], [3 4 5], 6}; n = cellfun(@numel, c);")
    assert np.asarray(s.workspace.get("n").backend_buffer()).tolist() == [
        [2.0, 3.0, 1.0]
    ]
    s = Session.create_default()
    ReplSession(s).run_line('run("tests/conformance/scripts/c10_cellfun.m");')
    assert np.asarray(s.workspace.get("n").backend_buffer()).tolist() == [
        [2.0, 3.0, 1.0]
    ]


def test_handle_value():
    s = Session.create_default()
    ReplSession(s).run_line("fh = @sum;")
    fh = s.workspace.get("fh")
    assert isinstance(fh, FunctionHandleValue)
    assert fh.matlab_class() == "function_handle"


def test_cellfun_char_function_name():
    """Issue #281: cellfun('name', C) resolves like @name (builtins and .m)."""
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, [1 2], []}; n = cellfun('numel', c); m = cellfun('sum', {[1 2], 3});")
    assert np.asarray(s.workspace.get("n").backend_buffer()).reshape(-1).tolist() == [1, 2, 0]
    assert np.asarray(s.workspace.get("m").backend_buffer()).reshape(-1).tolist() == [3, 3]


def test_cellfun_unknown_char_name_errors():
    s = Session.create_default()
    with pytest.raises(Exception, match="undefined function 'nope'"):
        ReplSession(s).run_line("n = cellfun('nope', {1});")
