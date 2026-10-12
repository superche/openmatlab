"""Anonymous functions @(x) expr and calling handles held in variables (Issue #280)."""

from __future__ import annotations

import io

import numpy as np
import pytest

from openmatlab.host.display import ConsoleDisplay
from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import AnonFuncExpr
from openmatlab.lang.parser import parse
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _get(code: str, name: str = "y"):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def test_parse_anon():
    (stmt,) = parse("f = @(x, y) x + y;")
    assert isinstance(stmt.value, AnonFuncExpr) and stmt.value.params == ("x", "y")


def test_call_anon_and_named_handle_from_variable():
    assert _get("f = @(x) x.^2 + 1; y = f(3);") == [10.0]
    assert _get("f = @(x, y) x * y; y = f(2, 3);") == [6.0]
    assert _get("f = @() 42; y = f();") == [42.0]
    assert _get("g = @abs; y = g(-2);") == [2.0]


def test_captures_values_at_creation():
    assert _get("a = 10; f = @(x) x + a; a = 0; y = f(1);") == [11.0]


def test_end_inside_anon_body():
    assert _get("f = @(v) v(end); y = f([4 5 6]);") == [6.0]


def test_anon_with_cellfun():
    assert _get("y = cellfun(@(v) numel(v) * 2, {1, [1 2]});") == [2.0, 4.0]


def test_too_many_inputs():
    with pytest.raises(EvalError, match="Too many input arguments"):
        _get("f = @(x) x; y = f(1, 2);")


def test_display_handles():
    s = Session.create_default()
    out = io.StringIO()
    s.display = ConsoleDisplay(workspace=s.workspace, stream=out)
    ReplSession(s).run_line("f = @(x) x.^2 + 1\ng = @sin")
    text = out.getvalue()
    assert "@(x)x.^2 + 1" in text and "@sin" in text
