from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/condition_stops.feature")


@pytest.fixture
def ctx():
    c = {}
    yield c
    if "repl" in c:
        c["repl"].run_line("dbclear all")


@given(parsers.parse('a fresh session with input lines "{lines}"'))
def fresh(ctx, lines):
    ctx["session"] = Session.create_default()
    ctx["repl"] = ReplSession(ctx["session"])
    ctx["repl"].feed_input(lines.split("|"))


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ctx["repl"].run_line(code)


@then(parsers.parse('variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(x.strip()) for x in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert list(got) == expected
