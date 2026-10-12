"""Nested and local functions in .m files; return exits the right frame (Issue #141)."""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(tmp_path: Path, files: dict, code: str, var: str = "r") -> float:
    for name, text in files.items():
        (tmp_path / f"{name}.m").write_text(text)
    s = Session.create_default()
    s.path.addpath(tmp_path)
    ReplSession(s).run_line(code)
    return float(s.workspace.get(var).backend_buffer().reshape(-1)[0])


def test_nested_shares_parent_variables(tmp_path):
    src = (
        "function y = outer(x)\n"
        "  a = 10;\n"
        "  bump(x);\n"
        "  y = a;\n"
        "  function bump(k)\n"
        "    a = a + k;\n"
        "  end\n"
        "end\n"
    )
    assert _run(tmp_path, {"outer": src}, "r = outer(5);") == 15.0


def test_nested_return_exits_only_nested_frame(tmp_path):
    src = (
        "function y = outer2()\n"
        "  y = 0;\n"
        "  step();\n"
        "  y = y + 100;\n"
        "  function step()\n"
        "    y = 1;\n"
        "    return;\n"
        "    y = 50;\n"
        "  end\n"
        "end\n"
    )
    # return leaves step() only; outer2 continues and adds 100.
    assert _run(tmp_path, {"outer2": src}, "r = outer2();") == 101.0


def test_nested_locals_are_private(tmp_path):
    src = (
        "function y = outer3()\n"
        "  y = helper(2);\n"
        "  function z = helper(w)\n"
        "    t = w * 3;\n"
        "    z = t;\n"
        "  end\n"
        "end\n"
    )
    assert _run(tmp_path, {"outer3": src}, "r = outer3();") == 6.0


def test_local_functions_in_file(tmp_path):
    src = (
        "function y = mainf(x)\n"
        "  y = sq(x) + 1;\n"
        "end\n"
        "function z = sq(w)\n"
        "  if w > 0\n"
        "    z = w * w;\n"
        "    return;\n"
        "  end\n"
        "  z = 0;\n"
        "end\n"
    )
    assert _run(tmp_path, {"mainf": src}, "r = mainf(3);") == 10.0
    # local function is not visible from the caller
    with pytest.raises(Exception):
        _run(tmp_path, {}, "r = sq(3);")
