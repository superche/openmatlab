"""Gherkin for the 2-by-2 lab layout (Epic #1011)."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/mitbih_labfigure.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh layout session")
def fresh(ctx):
    pass


@when(parsers.parse('I evaluate the layout "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('layout variable "{name}" equals scalar {val:g}'))
def scalar_eq(ctx, name, val):
    got = float(np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)[0])
    assert got == pytest.approx(val)


@then(parsers.parse('layout variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(x.strip()) for x in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer(), dtype=float).reshape(-1)
    assert np.allclose(got, expected)
