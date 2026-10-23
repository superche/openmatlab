"""Gherkin for the BBBC038 PNG and PDF export (Epic #1024)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytest.importorskip("numpy")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]
scenarios("../../features/bbbc038_export.feature")


@pytest.fixture
def ctx():
    return {"session": Session.create_default()}


@given("a fresh nuclei export session")
def fresh(ctx):
    pass


@when(parsers.parse('I export the nuclei layout to "{folder}"'))
def do_export(folder, ctx):
    Path(folder).mkdir(parents=True, exist_ok=True)
    code = (
        "fig_lab = figure('Visible','off','Position',[100 100 1200 900]); "
        "tl = tiledlayout(2, 2); tl.Title.String = 'BBBC038v1 stage1_test'; "
        "tl.XLabel.String = 'CC0 1.0. J. C. Caicedo et al., Nature Methods 16:1247-1253, 2019. BBBC038v1.'; "
        "nexttile; imshow(uint8(zeros(16, 16, 3))); title('BBBC038 raw'); "
        "nexttile; imshow(labeloverlay(uint8(zeros(16, 16)), ones(16))); title('BBBC038 overlay'); "
        "nexttile; histogram([117 152 219]); xlabel('Area (px)'); ylabel('Count'); "
        "nexttile; title('BBBC038 summary'); "
        f"exportgraphics(fig_lab, '{folder}/lab.png', 'Resolution', 300); "
        f"exportgraphics(fig_lab, '{folder}/lab.pdf', 'Resolution', 300); "
        f"png_info = dir('{folder}/lab.png'); pdf_info = dir('{folder}/lab.pdf'); "
        "png_bytes = png_info.bytes; pdf_bytes = pdf_info.bytes;"
    )
    ReplSession(ctx["session"]).run_line(code)


@then(parsers.parse('the nuclei export variable "{name}" is greater than {val:g}'))
def greater(ctx, name, val):
    got = float(np.asarray(ctx["session"].workspace.get(name).backend_buffer()).reshape(-1)[0])
    assert got > val
