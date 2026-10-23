"""M16 V06: lab-meeting tiledlayout on one BBBC038 FOV (Epic #1023).

The story builds the 2-by-2 figure and then closes it. The current figure
stays the 1-by-2 before/after panel, and the only other figure stays the
area histogram, which is what V03 and V04 already lock. This test rebuilds
the lab figure from ``lab_figure.m`` to inspect that layout.
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs import graphics_builtins as gb
from openmatlab.libs.labeloverlay import PALETTE
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()
FOOTNOTE = "CC0 1.0. J. C. Caicedo et al., Nature Methods 16:1247-1253, 2019. BBBC038v1."
AREAS = [152.0, 219.0, 143.0, 117.0, 193.0, 154.0]


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def _axes(fig):
    return [c for c in fig.children if c.alive and c.type == "axes"]


def _cdata(ax) -> np.ndarray:
    images = [c for c in ax.children if c.alive and c.type == "image"]
    assert len(images) == 1
    return np.asarray(images[0].props["CData"], dtype=float)


def test_v06_lab_figure_overlay_and_footnote():
    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "bbbc038" / "story_stage1_test.m"
    repl.run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "ncount") == 6
    assert _scalar(session, "meanarea") == 163
    assert _scalar(session, "medarea") == 153
    assert _scalar(session, "ntiles") == 2
    assert _scalar(session, "labtiles") == 4
    assert np.asarray(session.workspace.get("gs").backend_buffer()).reshape(-1).tolist() == [2.0, 2.0]
    assert session.workspace.get("footnote").text == FOOTNOTE
    assert "Nuclei 6" in session.workspace.get("summary").text
    assert "163" in session.workspace.get("summary").text
    assert "153" in session.workspace.get("summary").text

    image = np.asarray(session.workspace.get("I").backend_buffer())
    labels = np.asarray(session.workspace.get("L").backend_buffer())
    overlay = np.asarray(session.workspace.get("overlay").backend_buffer())
    assert overlay.dtype == np.uint8
    assert overlay.shape == (256, 256, 3)
    assert np.array_equal(overlay[labels == 0], image[labels == 0])
    expected = image.copy()
    for lab in range(1, 7):
        sel = labels == lab
        mixed = 0.5 * (image[sel] / 255.0) + 0.5 * PALETTE[lab - 1]
        expected[sel] = np.clip(np.rint(mixed * 255.0), 0, 255).astype(np.uint8)
    assert np.array_equal(overlay, expected)

    model = gb.model(session)
    current = model.gcf()
    layouts = [c for c in current.children if c.alive and c.type == "tiledlayout"]
    assert len(layouts) == 1
    assert list(layouts[0].props["GridSize"]) == [1.0, 2.0]
    others = [f for f in model.figures() if f is not current]
    assert len(others) == 1
    hist_axes = _axes(others[0])
    assert len(hist_axes) == 1
    assert hist_axes[0].props["Title"].props["String"] == "BBBC038 areas"

    lab = ROOT / "demos" / "bbbc038" / "lab_figure.m"
    repl.run_line(f'run("{lab.as_posix()}");')
    fig = model.gcf()
    layouts = [c for c in fig.children if c.alive and c.type == "tiledlayout"]
    assert len(layouts) == 1
    assert list(layouts[0].props["GridSize"]) == [2.0, 2.0]
    assert layouts[0].props["Title"].props["String"] == "BBBC038v1 stage1_test"
    assert layouts[0].props["XLabel"].props["String"] == FOOTNOTE
    axes = _axes(fig)
    assert [a.props["Title"].props["String"] for a in axes] == [
        "BBBC038 raw",
        "BBBC038 overlay",
        "Area (px)",
        "BBBC038 summary",
    ]
    assert axes[0].props["YDir"] == "reverse"
    assert axes[1].props["YDir"] == "reverse"
    assert np.allclose(_cdata(axes[0]), image.astype(float) / 255.0)
    assert np.allclose(_cdata(axes[1]), overlay.astype(float) / 255.0)
    assert axes[2].props["XLabel"].props["String"] == "Area (px)"
    assert axes[2].props["YLabel"].props["String"] == "Count"
    histograms = [c for c in axes[2].children if c.alive and c.type == "histogram"]
    assert len(histograms) == 1
    assert np.allclose(np.asarray(histograms[0].props["Data"], dtype=float), AREAS)
    summary = [c for c in axes[3].children if c.alive and c.type == "text"]
    assert any(c.props.get("String", "").startswith("Nuclei 6") for c in summary)
    assert axes[3].props["Visible"] == "off"
