"""Call stack: MException.stack, getReport, dbstack, mfilename, "Error in" (Epic #698)."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

F1 = "function f1()\n  a = 1;\n  g(a);\nend\nfunction g(a)\n  if a > 0\n    error('t:id', 'boom %d', a);\n  end\nend\n"


@pytest.fixture
def run(tmp_path):
    (tmp_path / "f1.m").write_text(F1)
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{tmp_path.as_posix()}');")

    def go(code):
        r.run_line(code)
        return s

    go.dir = tmp_path
    return go


def _num(s, name):
    return np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def _txt(s, name):
    return s.workspace.get(name).text


def test_stack_lines_inside_blocks(run):
    s = run("try, f1(); catch e, end; n = numel(e.stack); l1 = e.stack(1).line; l2 = e.stack(2).line; nm = e.stack(1).name;")
    assert _num(s, "n") == [2] and _num(s, "l1") == [7] and _num(s, "l2") == [3]
    assert _txt(s, "nm") == "f1>g"


def test_command_line_error_has_empty_stack(run):
    s = run("try, error('a:b', 'x'); catch e, end; sz = size(e.stack); r = getReport(e);")
    assert _num(s, "sz") == [0, 1] and _txt(s, "r") == "x"


def test_builtin_error_in_function_gets_stack(run):
    (run.dir / "bad.m").write_text("function bad()\n  x = [1 2] + [1 2 3];\nend\n")
    s = run("try, bad(); catch e, end; l = e.stack(1).line; nm = e.stack(1).name;")
    assert _num(s, "l") == [2] and _txt(s, "nm") == "bad"


def test_rethrow_keeps_stack_and_report_options(run):
    s = run("try, try, f1(); catch e0, rethrow(e0); end; catch e, end; l = e.stack(1).line;"
            " b = getReport(e, 'basic'); x = getReport(e, 'extended', 'hyperlinks', 'on');")
    assert _num(s, "l") == [7]
    assert _txt(s, "b") == "Error using f1>g (line 7)\nboom 1"
    assert _txt(s, "x") == "Error using f1>g (line 7)\nboom 1\n\nError in f1 (line 3)"


def test_getreport_bad_option_is_matlab_error(run):
    with pytest.raises(EvalError, match="invalid option"):
        run("e = MException('a:b', 'x'); getReport(e, 'verbose')")


def test_script_frame_and_mfilename(run):
    (run.dir / "scr.m").write_text("a = 1;\nst = dbstack;\nm = mfilename;\n")
    s = run("scr; n = numel(st); l = st(1).line; m0 = mfilename;")
    assert _num(s, "n") == [1] and _num(s, "l") == [2]
    assert _txt(s, "m") == "scr" and _txt(s, "m0") == ""


def test_dbstack_options_and_errors(run):
    (run.dir / "ds.m").write_text("function [a, b] = ds()\n  a = dbstack('-completenames');\n  b = dbstack(5);\nend\n")
    s = run("[a, b] = ds(); f = a(1).file; nb = numel(b);")
    assert _txt(s, "f").endswith("ds.m") and _txt(s, "f").startswith("/")
    assert _num(s, "nb") == [0]
    with pytest.raises(EvalError, match="dbstack"):
        run("dbstack(-1)")


def test_class_method_frame(run):
    (run.dir / "Kd.m").write_text("classdef Kd\n  methods\n    function m(o)\n      error('k:d', 'no');\n    end\n  end\nend\n")
    s = run("try, k = Kd(); k.m(); catch e, end; nm = e.stack(1).name; l = e.stack(1).line;")
    assert _txt(s, "nm") == "Kd.m" and _num(s, "l") == [4]


def test_cell_transpose(run):
    s = run("c = {1, 'a'; 2, 'b'}'; sz = size(c); v = c{1, 2};")
    assert _num(s, "sz") == [2, 2] and _num(s, "v") == [2]


def test_cli_prints_error_in_lines(tmp_path):
    (tmp_path / "f1.m").write_text(F1)
    p = subprocess.run([sys.executable, "-m", "openmatlab", "-e", f"addpath('{tmp_path.as_posix()}'); f1()"],
                       capture_output=True, text=True)
    assert p.returncode == 1
    assert "Error in f1>g (line 7)" in p.stderr and "Error in f1 (line 3)" in p.stderr
    assert "Traceback" not in p.stderr
