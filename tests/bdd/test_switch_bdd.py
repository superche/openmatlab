from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/switch_stmt.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh session")
def fresh(ctx):
    pass


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    # feature may embed \n escapes
    code = code.replace("\\n", "\n")
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals {value:d}'))
def var_eq(ctx, name, value):
    v = ctx["session"].workspace.get(name)
    assert float(v.backend_buffer().reshape(-1)[0]) == float(value)
