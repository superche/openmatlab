"""Gherkin for findgroups IncludeMissing, splitapply tables, and the group* slice (#1054, #1055)."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/grouping_1054_1055.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh grouping session")
def fresh(ctx):
    pass


@when(parsers.parse('I run "{code}"'))
def do_run(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('"{name}" is close to [{vals}]'))
def close_to(ctx, name, vals):
    expected = np.array([float(x.strip()) for x in vals.split(",")], float)
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer(), float).reshape(-1)
    assert got.shape == expected.shape
    assert np.allclose(got, expected, equal_nan=True)
