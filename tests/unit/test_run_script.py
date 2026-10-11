"""run("script.m") (Issue #36)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_run_absolute_script(tmp_path: Path):
    f = tmp_path / "init.m"
    f.write_text("a = 7;\nb = a * 2;\n")
    s = Session.create_default()
    ReplSession(s).run_line(f'run("{f}")')
    assert float(s.workspace.get("b").backend_buffer().reshape(-1)[0]) == 14.0


def test_run_via_path(tmp_path: Path):
    (tmp_path / "setup.m").write_text("z = 42;\n")
    s = Session.create_default()
    ReplSession(s).run_line(f'addpath("{tmp_path}")')
    ReplSession(s).run_line('run("setup")')
    assert float(s.workspace.get("z").backend_buffer().reshape(-1)[0]) == 42.0


def test_run_rejects_function_file(tmp_path: Path):
    (tmp_path / "add2.m").write_text(
        "function y = add2(a, b)\ny = a + b;\nend\n"
    )
    s = Session.create_default()
    ReplSession(s).run_line(f'addpath("{tmp_path}")')
    with pytest.raises(EvalError, match="function file"):
        ReplSession(s).run_line('run("add2")')


def test_run_script_with_while(tmp_path: Path):
    f = tmp_path / "loop.m"
    f.write_text("n = 0;\nwhile n < 3\nn = n + 1;\nend\n")
    s = Session.create_default()
    ReplSession(s).run_line(f'run("{f}")')
    assert float(s.workspace.get("n").backend_buffer().reshape(-1)[0]) == 3.0
