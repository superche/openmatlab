from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/cell_paren_index.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh session")
def fresh(ctx):
    ctx["session"] = Session.create_default()


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('char variable "{name}" equals "{value}"'))
def char_eq(ctx, name, value):
    assert ctx["session"].workspace.get(name).text == value
