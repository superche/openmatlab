"""Gherkin for the record-100 PNG and PDF export (Epic #1012)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]
scenarios("../../features/mitbih_export.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh export session")
def fresh(ctx):
    pass


@when(parsers.parse('I export the lab layout to "{folder}"'))
def do_export(folder, ctx):
    Path(folder).mkdir(parents=True, exist_ok=True)
    code = (
        "fig_lab = figure('Visible','off','Position',[100 100 1200 900]); "
        "tl = tiledlayout(2, 2); tl.Title.String = 'MIT-BIH record 100'; "
        "tl.XLabel.String = 'DOI 10.13026/C2F305'; "
        "nexttile; plot(1:8); nexttile; plot(1:8); nexttile; histogram(1:6); nexttile; plot(1:8); "
        f"exportgraphics(fig_lab, '{folder}/lab.png', 'Resolution', 300); "
        f"exportgraphics(fig_lab, '{folder}/lab.pdf', 'Resolution', 300); "
        f"png_info = dir('{folder}/lab.png'); pdf_info = dir('{folder}/lab.pdf'); "
        "png_bytes = png_info.bytes; pdf_bytes = pdf_info.bytes;"
    )
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('export variable "{name}" is greater than {val:g}'))
def greater(ctx, name, val):
    got = float(np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)[0])
    assert got > val
