from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/timetable.feature")


@pytest.fixture
def ctx():
    return {}


@given(parsers.parse('the MATLAB code "{code}"'))
def code(ctx, code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    ctx["s"] = s


@then(parsers.parse('v equals "{vals}"'))
def eq(ctx, vals):
    got = np.asarray(ctx["s"].workspace.get("v").backend_buffer(), float).reshape(-1).tolist()
    assert got == [float(x) for x in vals.split()]
