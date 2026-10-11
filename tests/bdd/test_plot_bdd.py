from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")
pytest.importorskip("matplotlib")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [
    pytest.mark.bdd,
    pytest.mark.unit,
    pytest.mark.needs_numpy,
    pytest.mark.needs_matplotlib,
]

scenarios("../../features/plot_mvp.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh plotting session")
def fresh(ctx):
    ctx["session"] = Session.create_default()


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse("the last figure has {n:d} line"))
@then(parsers.parse("the last figure has {n:d} lines"))
def fig_lines(ctx, n):
    fig = ctx["session"].graphics.last_figure
    assert fig is not None
    assert len(fig.axes[0].lines) == n
