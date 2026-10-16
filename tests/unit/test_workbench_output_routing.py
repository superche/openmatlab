"""#760 / M13 G-E0: script and builtin output in the Workbench goes to the Command Window."""

from __future__ import annotations

import sys
import threading

import pytest

from openmatlab.host.workbench import Workbench

pytestmark = pytest.mark.unit


def test_run_file_output_lands_in_command_window(tmp_path, capsys):
    (tmp_path / "s.m").write_text("fprintf('total = %d\\n', 7);\ndisp('hello')\nwarning('w:x','careful');\n")
    wb = Workbench.create(cwd=tmp_path)
    wb.run_file(tmp_path / "s.m")
    text = wb.command_window.text()
    assert "total = 7" in text and "hello" in text and "Warning: careful" in text
    cap = capsys.readouterr()
    assert "total = 7" not in cap.out and "careful" not in cap.err


def test_eval_returns_fprintf_and_stderr_text(tmp_path):
    wb = Workbench.create(cwd=tmp_path)
    out = wb.eval("fprintf('a%d\\n', 1); fprintf(2, 'oops\\n'); disp(2)")
    assert out == "a1\noops\n2\n"


def test_output_before_error_and_error_text_in_order(tmp_path):
    wb = Workbench.create(cwd=tmp_path)
    out = wb.eval("fprintf('before\\n'); error('my:id', 'bad thing')")
    assert out.index("before") < out.index("bad thing")
    assert "Traceback" not in out


def test_function_file_output_routed(tmp_path):
    (tmp_path / "f.m").write_text("function f()\nfprintf('in f\\n');\nend\n")
    wb = Workbench.create(cwd=tmp_path)
    assert "in f" in wb.eval("f()")


def test_evalc_still_captures_inside_workbench(tmp_path):
    wb = Workbench.create(cwd=tmp_path)
    wb.eval("s = evalc('fprintf(''x'')');")
    assert wb.eval_value("s") == "x"
    assert "x" not in wb.command_window.text().replace("s = evalc", "")


def test_other_threads_not_routed(tmp_path, capsys):
    wb = Workbench.create(cwd=tmp_path)
    wb.eval("disp(1)")
    t = threading.Thread(target=lambda: print("terminal-only"))
    t.start()
    t.join()
    assert "terminal-only" not in wb.command_window.text()
    assert "terminal-only" in capsys.readouterr().out


def test_two_workbenches_isolated(tmp_path):
    a, b = Workbench.create(cwd=tmp_path), Workbench.create(cwd=tmp_path)
    a.eval("fprintf('A\\n')")
    b.eval("fprintf('B\\n')")
    assert "B" not in a.command_window.text() and "A" not in b.command_window.text()
    assert sys.stdout is not None
