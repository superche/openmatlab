from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/ode_quad_opt.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(x.strip()) for x in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert np.allclose(got, expected)
