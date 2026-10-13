"""Epic #530: try/catch, error, MException, throw/rethrow, assert, lasterr."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.lang.ast_nodes import TryStmt
from openmatlab.host.repl import ReplSession
from openmatlab.lang.parser import parse
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _num(s, name):
    return float(np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1)[0])


def _txt(s, name):
    return s.workspace.get(name).text


def test_parse_try_catch_ident():
    stmts = parse("try\n x=1;\ncatch err\n y=2;\nend\n")
    t = stmts[0]
    assert isinstance(t, TryStmt) and t.ident == "err" and len(t.body) == 1 and len(t.handler) == 1


def test_parse_catch_call_is_handler_not_ident():
    t = parse("try, error('q'), catch disp('h'), end")[0]
    assert t.ident is None and len(t.handler) == 1


def test_try_without_catch_swallows():
    s = _run("x = 1; try, error('boom'); x = 2; end")
    assert _num(s, "x") == 1


def test_error_single_arg_is_literal():
    s = _run("try, error('100%% \\n'); catch e, m = e.message; end")
    assert _txt(s, "m") == "100%% \\n"


def test_error_id_format():
    s = _run("try, error('a:b', '%s-%d', 'x', 4); catch e, m = e.message; i = e.identifier; end")
    assert _txt(s, "m") == "x-4" and _txt(s, "i") == "a:b"


def test_error_non_id_first_arg_formats():
    s = _run("try, error('val %d', 9); catch e, m = e.message; i = e.identifier; end")
    assert _txt(s, "m") == "val 9" and _txt(s, "i") == ""


def test_error_empty_is_noop():
    s = _run("error(''); x = 3;")
    assert _num(s, "x") == 3


def test_uncaught_error_is_evalerror_with_identifier():
    with pytest.raises(EvalError) as ei:
        _run("error('top:id', 'boom')")
    assert str(ei.value) == "boom" and ei.value.identifier == "top:id"


def test_mexception_invalid_id_rejected():
    with pytest.raises(EvalError, match="not a valid message identifier"):
        _run("MException('bad', 'x')")


def test_isstruct_false_for_mexception():
    s = _run("e = MException('a:b', 'm'); k = isstruct(e); c = class(e);")
    assert _num(s, "k") == 0 and _txt(s, "c") == "MException"


def test_return_inside_try_in_function_not_caught(tmp_path):
    (tmp_path / "f530.m").write_text("function y = f530()\ny = 1;\ntry\n  return\ncatch\n  y = 99;\nend\ny = 2;\nend\n")
    s = _run(f"addpath('{tmp_path}'); r = f530();")
    assert _num(s, "r") == 1


def test_error_from_function_caught_by_caller(tmp_path):
    (tmp_path / "g530.m").write_text("function g530()\nerror('g:x', 'inner %d', 5);\nend\n")
    s = _run(f"addpath('{tmp_path}'); try, g530(); catch e, m = e.message; i = e.identifier; end")
    assert _txt(s, "m") == "inner 5" and _txt(s, "i") == "g:x"


def test_lasterr_two_outputs():
    s = _run("try, error('z:w', 'last'); catch, end; [m, i] = lasterr;")
    assert _txt(s, "m") == "last" and _txt(s, "i") == "z:w"


def test_assert_default_message_and_id():
    s = _run("try, assert(false); catch e, m = e.message; i = e.identifier; end")
    assert _txt(s, "m") == "Assertion failed." and _txt(s, "i") == "MATLAB:assertion:failed"


def test_assert_empty_condition_fails():
    with pytest.raises(EvalError):
        _run("assert([])")


def test_dimension_mismatch_identifier():
    s = _run("try, [1 2] + [1 2 3]; catch e, i = e.identifier; end")
    assert _txt(s, "i") == "MATLAB:sizeDimensionsMustMatch"


def test_display_header_mexception():
    from openmatlab.host.repl import ReplSession
    import io, contextlib

    import subprocess, sys

    out = subprocess.run([sys.executable, "-m", "openmatlab.host.cli", "-e", "e = MException('a:b', 'm')"],
                         capture_output=True, text=True).stdout
    assert "MException with properties:" in out
