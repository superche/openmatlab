from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/workbench_debug.feature")

SRC = "function y = wbb(x)\n  a = x + 1;\n  y = subb(a);\nend\nfunction z = subb(b)\n  z = b * 2;\nend\n"


@pytest.fixture
def ctx():
    c = {}
    yield c
    wb = c.get("wb")
    if wb is not None:
        if wb.debug.is_paused():
            wb.debug.quit()
        wb.eval("dbclear all")


@given(parsers.parse('a workbench with function file "{name}"'))
def make_wb(ctx, tmp_path, name):
    (tmp_path / name).write_text(SRC)
    ctx["wb"] = Workbench.create(cwd=tmp_path)
    ctx["ed"] = ctx["wb"].documents.open_file(tmp_path / name)


@when(parsers.parse('I toggle a breakpoint on line {line:d} and run "{code}"'))
def toggle_run(ctx, line, code):
    ctx["ed"].toggle_breakpoint(line)
    ctx["wb"].debug.run(code)


@when("I press Continue")
def cont(ctx):
    ctx["wb"].debug.continue_()


@when(parsers.parse("I select stack frame {k:d}"))
def select(ctx, k):
    ctx["wb"].debug.select_frame(k)


@then(parsers.parse("the debugger is paused at line {line:d}"))
def paused_at(ctx, line):
    assert ctx["wb"].debug.is_paused() and ctx["wb"].debug.current_line() == line


@then(parsers.parse('variable "{name}" in the workbench equals {val:d}'))
def var_eq(ctx, name, val):
    assert ctx["wb"].eval_value(name) == val


@then(parsers.parse('the Workspace panel shows "{name}"'))
def ws_shows(ctx, name):
    assert name in ctx["wb"].workspace.names()
