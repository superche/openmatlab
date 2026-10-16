"""M12 C-E6 (Epic #766): the two internal crashes from the first full corpus run (C09)."""

from __future__ import annotations

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError

pytestmark = pytest.mark.unit


def _out(capsys, line):
    ReplSession().run_line(line)
    return capsys.readouterr().out


def test_star_width_and_precision(capsys):
    assert _out(capsys, "fprintf('%-*s|%*d|%.*f\\n', 4, 'ab', 3, 7, 2, pi);") == "ab  |  7|3.14\n"


def test_negative_star_width_left_aligns(capsys):
    assert _out(capsys, "fprintf('[%*d]\\n', -3, 5);") == "[5  ]\n"


def test_star_needs_integer():
    with pytest.raises(EvalError):
        ReplSession().run_line("sprintf('%*d', 1.5, 2)")


def test_display_inside_function_does_not_crash(tmp_path, capsys):
    (tmp_path / "showit.m").write_text("function showit()\n  display('hello')\nend\n")
    r = ReplSession()
    r.run_line(f"addpath('{tmp_path}');")
    r.run_line("showit()")
    assert "hello" in capsys.readouterr().out
