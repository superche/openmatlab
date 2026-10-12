"""MATLAB display / ans semantics (Issue #406)."""

from __future__ import annotations

import io

import pytest

from openmatlab.host.display import ConsoleDisplay
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code: str):
    s = Session.create_default()
    out = io.StringIO()
    s.display = ConsoleDisplay(workspace=s.workspace, stream=out)
    ReplSession(s).run_line(code)
    labels = [ln[:-2] for ln in out.getvalue().splitlines() if ln.endswith(" =")]
    return s, labels


def test_bare_variable_shows_own_name_and_leaves_ans():
    s, labels = _run("y = 1;\ny")
    assert labels == ["y"]
    assert "ans" not in s.workspace


def test_assignments_never_bind_ans():
    s, labels = _run("x = 3\n[m, n] = size([1 2 3])\nA = zeros(1, 2);\nA(2) = 5\nc = {1};\nc{1} = 2")
    assert labels == ["x", "m", "n", "A", "c"]
    assert "ans" not in s.workspace


def test_expression_binds_ans_even_when_suppressed():
    s, labels = _run("3 + 1;\nans")
    assert labels == ["ans"]
    assert float(s.workspace.get("ans").backend_buffer().reshape(-1)[0]) == 4.0


def test_blocks_display_inner_statements_not_themselves():
    s, labels = _run("for i = 1:2\ni\nend\nif true\nz = 5\nend\nk = 0;\nwhile k < 1\nk = k + 1;\nend")
    assert labels == ["i", "i", "z"]
    assert "ans" not in s.workspace
