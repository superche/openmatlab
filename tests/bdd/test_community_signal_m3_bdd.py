from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/community_signal_m3.feature")
MFILES = Path(__file__).resolve().parents[2] / "demos" / "plugins" / "community.signal" / "mfiles"


@pytest.fixture
def ctx():
    s = Session.create_default()
    ReplSession(s).run_line(f"addpath('{MFILES.as_posix()}');")
    return {"session": s}


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(x.strip()) for x in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert np.allclose(got, expected)
