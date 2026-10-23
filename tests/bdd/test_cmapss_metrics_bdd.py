"""Gherkin for FD001 degradation metrics (Epic #996)."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/cmapss_metrics.feature")


@pytest.fixture
def ctx():
    session = Session.create_default()
    demo = (repo_root() / "demos" / "cmapss").as_posix()
    ReplSession(session).run_line(f"addpath('{demo}');")
    return {"session": session}


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(x.strip()) for x in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert np.allclose(got, expected)
