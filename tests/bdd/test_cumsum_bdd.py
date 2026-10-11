from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")
import numpy as np

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/cumsum.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh session")
def fresh(ctx):
    ctx["session"] = Session.create_default()


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals {value:d} at last'))
def last_eq(ctx, name, value):
    buf = np.asarray(ctx["session"].workspace.get(name).backend_buffer())
    assert float(buf.reshape(-1)[-1]) == float(value)
