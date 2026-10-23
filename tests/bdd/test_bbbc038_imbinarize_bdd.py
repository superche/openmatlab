"""Gherkin for global imbinarize and bwareaopen (Epic #1021)."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/bbbc038_imbinarize.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a uint8 row of six intensities")
def intensities(ctx):
    ReplSession(ctx["session"]).run_line("I = uint8([0 0 10 10 200 200]);")


@given("a binary speck beside a block")
def speck(ctx):
    ReplSession(ctx["session"]).run_line("BW = logical([1 0 0 0; 1 0 1 1; 0 0 1 1]);")


@when(parsers.parse('I evaluate the mask "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('the mask variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(item.strip()) for item in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert list(got) == expected
