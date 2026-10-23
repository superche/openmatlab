"""Gherkin for labeloverlay (Epic #1023)."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/bbbc038_labeloverlay.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a one-pixel black image labeled 1")
def black_pixel(ctx):
    ReplSession(ctx["session"]).run_line("A = uint8(zeros(1, 1)); L = 1;")


@when(parsers.parse('I evaluate the overlay "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse("the overlay variable \"{name}\" equals uint8 [{vals}]"))
def uint8_eq(ctx, name, vals):
    expected = [int(item.strip()) for item in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert got.tolist() == expected
