"""Gherkin for lab-meeting PNG and PDF export (Epic #998)."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import parsers, scenarios, then, when

pytest.importorskip("numpy")
pytest.importorskip("matplotlib")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]
scenarios("../../features/export_story.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals scalar {val:d}'))
def scalar_eq(ctx, name, val):
    got = float(np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)[0])
    assert got == float(val)
