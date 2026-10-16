from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/workbench_workflows.feature")

SCRIPT = "%% one\na = 1;\n%% two\nb = a + 1;\n%% three\nc = b * 10;\n"
BAD = "function bad_wf()\n  x = 1;\n  error('wf:e', 'oops');\nend\n"


@pytest.fixture
def ctx():
    return {}


@given("a workbench with a three-section script open")
def make(ctx, tmp_path):
    (tmp_path / "sec_wf.m").write_text(SCRIPT)
    (tmp_path / "bad_wf.m").write_text(BAD)
    ctx["wb"] = Workbench.create(cwd=tmp_path)
    ctx["wb"].documents.open_file(tmp_path / "sec_wf.m")


@when("I press Run and Advance twice")
def adv(ctx):
    ctx["wb"].run_and_advance()
    ctx["wb"].run_and_advance()


@when(parsers.parse('I run "{code}" in the Command Window'))
def run(ctx, code):
    ctx["wb"].eval(code)


@when("I follow the error link")
def follow(ctx):
    ctx["wb"].open_error_link()


@then(parsers.parse('variable "{name}" in the workbench equals {val:g}'))
def var(ctx, name, val):
    assert ctx["wb"].eval_value(name) == val


@then(parsers.parse("the editor caret is on line {n:d}"))
def caret(ctx, n):
    assert ctx["wb"].editor.cursor_line() == n


@then(parsers.parse('the editor shows "{name}" at line {n:d}'))
def shows(ctx, name, n):
    assert ctx["wb"].editor.tab_title == name and ctx["wb"].editor.cursor_line() == n
