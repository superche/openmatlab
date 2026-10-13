"""Epic #610 (M7 C11): evalin/assignin frames and doc/lookfor/what."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime import frames
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _session(tmp_path, files=None):
    for name, src in (files or {}).items():
        (tmp_path / f"{name}.m").write_text(src)
    s = Session.create_default()
    ReplSession(s).run_line(f"addpath('{tmp_path}');")
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer()).item()


SETX = """function setx(v)
% SETX assigns x in the caller workspace.
assignin('caller', 'x', v);
assignin('base', 'fromf', evalin('caller', 'y + 1'));
mid();
end
function mid()
assignin('caller', 'midset', 1);
leaf();
end
function leaf()
assignin('caller', 'leafset', 2);
assignin('base', 'deep', evalin('base', 'y'));
end
"""


def test_caller_and_base_resolution_through_nested_calls(tmp_path):
    s = _session(tmp_path, {"setx": SETX})
    ReplSession(s).run_line("y = 41; setx(5);")
    assert _v(s, "x") == 5 and _v(s, "fromf") == 42 and _v(s, "deep") == 41
    assert "midset" not in s.workspace.names() and "leafset" not in s.workspace.names()


def test_frame_stack_unwinds_on_error(tmp_path):
    s = _session(tmp_path, {"boom": "function boom()\nerror('my:id', 'x');\nend\n"})
    with pytest.raises(EvalError):
        ReplSession(s).run_line("boom();")
    assert frames.depth() == 0


def test_evalin_catch_string_and_value_form():
    s = Session.create_default()
    ReplSession(s).run_line("r = evalin('base', 'nope_zz', '-1'); q = evalin('caller', '2 + 3');")
    assert _v(s, "r") == -1 and _v(s, "q") == 5


def test_invalid_context_and_name():
    with pytest.raises(EvalError, match="'base' or 'caller'"):
        ReplSession(Session.create_default()).run_line("evalin('nowhere', '1');")
    with pytest.raises(EvalError, match="Invalid variable name"):
        ReplSession(Session.create_default()).run_line("assignin('base', 'for', 1);")


def test_anonymous_function_caller_is_invoking_workspace():
    s = Session.create_default()
    ReplSession(s).run_line("y = 7; f = @() evalin('caller', 'y'); a = f(); c = cellfun(@(k) evalin('caller', 'y') + k, {1, 2});")
    assert _v(s, "a") == 7
    assert np.asarray(s.workspace.get("c").backend_buffer()).tolist() == [[8, 9]]


def test_str2num_nested_session_is_isolated():
    s = Session.create_default()
    ReplSession(s).run_line("y = 3; v = str2num('4');")
    assert _v(s, "v") == 4 and frames.depth() == 0


def test_doc_lookfor_what(tmp_path, capsys):
    s = _session(tmp_path, {"probe": "function probe()\n% PROBE Unicorn helper line.\nend\n"})
    (tmp_path / "data.mat").write_bytes(b"")
    ReplSession(s).run_line("doc probe")
    assert "PROBE Unicorn" in capsys.readouterr().out
    ReplSession(s).run_line("lookfor unicorn")
    assert "probe - PROBE Unicorn helper line." in capsys.readouterr().out
    ReplSession(s).run_line(f"what('{tmp_path}')")
    out = capsys.readouterr().out
    assert "MATLAB Code files" in out and "probe" in out and "data.mat" in out
    ReplSession(s).run_line(f"w = what('{tmp_path}'); n = numel(w.mat);")
    assert _v(s, "n") == 1
    ReplSession(s).run_line("doc nonexistent_zz")
    assert "No documentation found" in capsys.readouterr().out
