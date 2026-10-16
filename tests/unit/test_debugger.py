"""Debug engine: dbstop/dbclear/dbstatus, stepping, paused workspace, dbquit (Epic #699)."""

from __future__ import annotations

import time

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime import debugger
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

Q2 = "function y = q2(x)\n  y = x + 1;\n\n  y = y * 2;\nend\n"


@pytest.fixture
def env(tmp_path):
    (tmp_path / "q2.m").write_text(Q2)
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}');")
    yield s, r, tmp_path
    r.run_line("dbclear all")


def _num(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer()).reshape(-1).tolist()


def test_line_snaps_to_next_executable(env):
    s, r, _ = env
    r.run_line("dbstop in q2 at 3; st = dbstatus('q2'); l = st.line;")
    assert _num(s, "l") == [4]


def test_dbstatus_printed_and_clear_in(env, capsys):
    s, r, _ = env
    r.run_line("dbstop in q2 at 2; dbstop in q2 at 4; out = evalc('dbstatus'); dbclear in q2; e = isempty(dbstatus);")
    assert "Breakpoints for q2 are on lines 2, 4." in s.workspace.get("out").text
    assert _num(s, "e") == [1]


def test_assignment_while_paused_takes_effect(env):
    s, r, _ = env
    r.feed_input(["y = 100;", "dbcont"])
    r.run_line("dbstop in q2 at 4; v = q2(1);")
    assert _num(s, "v") == [200]


def test_dbquit_unwinds_past_try_catch(env, tmp_path):
    s, r, _ = env
    (tmp_path / "w.m").write_text("function w()\n  try\n    q2(1);\n  catch\n    disp('caught');\n  end\nend\n")
    r.feed_input(["dbquit"])
    r.run_line("dbstop in q2 at 2; w(); after = 1;")
    assert "after" not in s.workspace.names()
    assert not s.debugger.paused


def test_eof_while_paused_quits(env):
    s, r, _ = env
    r.run_line("dbstop in q2 at 2;")
    r.feed_input([])
    s.debugger.read_line = lambda prompt: None
    r.run_line("v = q2(1);")
    assert "v" not in s.workspace.names()


def test_errors_at_k_prompt_do_not_resume(env, capsys):
    s, r, _ = env
    r.feed_input(["nosuch_zz", "dbcont"])
    r.run_line("dbstop in q2 at 2; v = q2(1);")
    assert _num(s, "v") == [4]


def test_dbstep_n_and_conditional(env):
    s, r, tmp = env
    (tmp / "lp.m").write_text("function t = lp()\n  t = 0;\n  for k = 1:5\n    t = t + k;\n  end\nend\n")
    r.feed_input(["global KS; KS(end+1) = k;", "dbcont"])
    r.run_line("global KS; KS = []; dbstop in lp at 4 if k == 3; t = lp();")
    assert _num(s, "KS") == [3] and _num(s, "t") == [15]


@pytest.mark.parametrize("cmd", ["dbcont", "dbstep", "dbquit", "dbup", "dbdown"])
def test_commands_outside_debug_mode_are_errors(env, cmd):
    _s, r, _ = env
    with pytest.raises(EvalError, match="only valid when stopped"):
        r.run_line(cmd)


@pytest.mark.parametrize("cmd,msg", [
    ("dbstop in nosuchfn_zz", "Cannot find function"),
    ("dbstop in q2 at 99", "no executable line"),
    ("dbstop if bogus", "unknown condition"),
    ("dbstop", "specify a location"),
])
def test_dbstop_errors(env, cmd, msg):
    _s, r, _ = env
    with pytest.raises(EvalError, match=msg):
        r.run_line(cmd)


def test_hook_overhead_without_breakpoints(env):
    s, r, _ = env
    r.run_line("dbclear all")
    assert debugger.ON is False
    code = "t = 0; for k = 1:20000, t = t + k; end"
    t0 = time.perf_counter(); r.run_line(code); base = time.perf_counter() - t0
    debugger.ON = True  # force the guarded branch (no breakpoints: lookup only)
    try:
        t0 = time.perf_counter(); r.run_line(code); forced = time.perf_counter() - t0
    finally:
        debugger._recompute_on()
    assert forced < base * 1.5 + 0.05
