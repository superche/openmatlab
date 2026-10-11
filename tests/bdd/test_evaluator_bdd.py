from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]

scenarios("../../features/evaluator.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh session")
def fresh(ctx):
    ctx["session"] = Session.create_default()


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" has shape {r:d} by {c:d}'))
def var_shape(ctx, name, r, c):
    v = ctx["session"].workspace.get(name)
    assert v.shape == (r, c)


@then(parsers.parse("ans equals {value:d}"))
def ans_equals(ctx, value):
    ans = ctx["session"].workspace.get("ans")
    assert float(ans.backend_buffer().reshape(-1)[0]) == float(value)
