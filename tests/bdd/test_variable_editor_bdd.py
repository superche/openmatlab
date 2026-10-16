from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.host.variable_editor import VariableEditError
from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/variable_editor.feature")


@pytest.fixture
def ctx():
    return {}


@given(parsers.parse('a workbench where "{code}" has run'))
def wb(ctx, tmp_path, code):
    ctx["wb"] = Workbench.create(cwd=tmp_path)
    ctx["wb"].eval(code)


@when(parsers.parse('I open "{name}" in the variable editor and set cell {r:d},{c:d} to "{text}"'))
def edit(ctx, name, r, c, text):
    try:
        ctx["wb"].variable_editor.open(name).set_cell(r, c, text)
    except VariableEditError as e:
        ctx["err"] = str(e)


@then("the variable editor reports an error")
def err(ctx):
    assert ctx.get("err")


@then(parsers.parse('the workbench value of "{expr}" is {val:g}'))
def val(ctx, expr, val):
    assert float(ctx["wb"].eval_value(expr)) == val
