"""keyboard, input, and condition stops: error / caught error / warning / naninf (Epic #700)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

FILES = {
    "kb7.m": "function r = kb7()\n  v = 1;\n  keyboard\n  r = v;\nend\n",
    "er7.m": "function er7()\n  a = [1 2];\n  b = a(5);\nend\n",
    "ce7.m": "function ce7()\n  try\n    error('x7:id', 'boom');\n  catch\n  end\nend\n",
    "wn7.m": "function wn7()\n  warning('w7:id', 'careful');\nend\n",
    "nf7.m": "function nf7()\n  q = 1;\n  z = 0 / 0;\nend\n",
}


@pytest.fixture
def env(tmp_path):
    for n, src in FILES.items():
        (tmp_path / n).write_text(src)
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}'); global L7; L7 = [];")
    yield s, r
    r.run_line("dbclear all")


REC = "global L7; s_ = dbstack; L7(end+1) = s_(1).line;"


def _num(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer()).reshape(-1).tolist()


def test_input_forms(env):
    s, r = env
    r.feed_input(["2*3", "abc", "", "1 +", "5"])
    r.run_line("a = input('a: '); b = input('b: ', 's'); c = isempty(input('')); d = input('d: ');")
    assert _num(s, "a") == [6]
    assert s.workspace.get("b").text == "abc"
    assert _num(s, "c") == [True]
    assert _num(s, "d") == [5]  # a bad reply is reported and asked again


def test_input_sees_caller_workspace_and_eof(env, monkeypatch):
    s, r = env
    monkeypatch.setattr("builtins.input", lambda *a: (_ for _ in ()).throw(EOFError()))
    r.feed_input(["k + 1"])
    r.run_line("k = 41; a = input('');")
    assert _num(s, "a") == [42]
    r.run_line("try, input('x'); e = ''; catch err, e = err.identifier; end")
    assert s.workspace.get("e").text == "MATLAB:input:EndOfInput"


def test_keyboard_then_dbcont(env):
    s, r = env
    r.feed_input(["v = 7;", "dbcont"])
    r.run_line("x = kb7();")
    assert _num(s, "x") == [7]


def test_keyboard_dbquit_stops_run(env):
    s, r = env
    r.feed_input(["dbquit"])
    r.run_line("x = kb7(); y = 1;")
    assert "y" not in s.workspace.names()


def test_uncaught_error_stop_at_faulting_line(env, capsys):
    s, r = env
    r.feed_input([REC, "dbcont"])
    with pytest.raises(EvalError):  # dbcont lets the error continue to the prompt
        r.run_line("dbstop if error; er7();")
    r.run_line("global L7; l = L7;")
    assert _num(s, "l") == [3]


def test_caught_error_with_and_without_id(env):
    s, r = env
    r.feed_input([REC, "dbcont"])
    r.run_line("dbstop if caught error x7:id; ce7(); dbclear all; dbstop if caught error other:id; ce7();")
    r.run_line("dbstop if error; ce7(); global L7; l = L7;")  # 'if error' ignores caught errors
    assert _num(s, "l") == [3]


def test_warning_and_naninf(env):
    s, r = env
    r.feed_input([REC, "dbcont", REC, "dbcont"])
    r.run_line("dbstop if warning w7:id; wn7(); dbclear all; dbstop if naninf; nf7(); dbclear all; global L7; l = L7;")
    assert _num(s, "l") == [2, 3]


def test_errors_are_matlab_errors(env):
    s, r = env
    for code in ["input()", "input(5)", "input('a', 'q')", "keyboard(1)"]:
        r.run_line(f"try, {code}; e = 'none'; catch err, e = err.message; end")
        msg = s.workspace.get("e").text
        assert msg != "none" and "internal error" not in msg
