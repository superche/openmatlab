"""Gherkin for heatmap (Epic #997)."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_bdd import parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/heatmap.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@when(parsers.parse('I evaluate "{code}"'))
def do_eval(code, ctx):
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('variable "{name}" equals text "{text}"'))
def text_eq(ctx, name, text):
    assert ctx["session"].workspace.get(name).text == text


@then(parsers.parse('variable "{name}" equals row [{vals}]'))
def row_eq(ctx, name, vals):
    expected = [float(x.strip()) for x in vals.split(",")]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)
    assert np.allclose(got, expected)


@then(parsers.parse("variable \"{name}\" equals matrix [{row1}; {row2}]"))
def matrix_eq(ctx, name, row1, row2):
    expected = [[float(x) for x in row.split()] for row in (row1, row2)]
    got = np.asarray(ctx["session"].workspace.get(name).backend_buffer(), dtype=float)
    assert np.allclose(got, expected)


@then(parsers.parse("variable \"{name}\" equals text row [{vals}]"))
def text_row(ctx, name, vals):
    expected = [x.strip() for x in vals.split(",")]
    value = ctx["session"].workspace.get(name)
    got = [item.text for row in value.rows for item in row]
    assert got == expected
