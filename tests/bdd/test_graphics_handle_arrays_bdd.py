from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import parsers, scenarios, then, when

pytest.importorskip("matplotlib")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]
scenarios("../../features/graphics_handle_arrays.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


def _vals(vals):
    return [float(x.strip()) for x in vals.split(",")]


@then(parsers.parse('variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer())
    assert got.shape[0] == 1 and list(got.reshape(-1)) == _vals(vals)


@then(parsers.parse('variable "{name}" equals column [{vals}]'))
def col_eq(ctx, name, vals):
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer())
    assert got.shape[1] == 1 and list(got.reshape(-1).astype(float)) == _vals(vals)


@then(parsers.parse('variable "{name}" is the text "{text}"'))
def text_eq(ctx, name, text):
    assert ctx["session"].workspace.get(name).text == text
