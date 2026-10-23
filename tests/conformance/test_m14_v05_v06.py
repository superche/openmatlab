"""M14 V05/V06: heatmap correlation panel and the lab-meeting figure (Epic #997).

The story still ends on the V03 smoothdata axes. This test checks the figure
created before that one: a 2-by-3 tiledlayout, sensor traces, early/late,
a heatmap of C with a colorbar and sensor tick labels, failure cycles, train
RUL, the unit id, and the Saxena / Zenodo footnote.
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()
DOI = "10.5281/zenodo.15346912"


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def _texts(value) -> list:
    return [item.text for row in value.rows for item in row]


def _axes_titled(fig, fragment: str):
    hits = [ax for ax in fig.axes if fragment in (ax.get_title() or "")]
    assert hits, f"no axes titled with {fragment!r}"
    return hits[0]


def _rendered_text(fig) -> str:
    parts = []
    sup = getattr(fig, "_suptitle", None)
    if sup is not None:
        parts.append(sup.get_text())
    parts.extend(t.get_text() for t in fig.texts)
    for ax in fig.axes:
        parts.append(ax.get_title() or "")
        parts.append(ax.get_xlabel() or "")
        parts.append(ax.get_ylabel() or "")
        parts.extend(t.get_text() for t in ax.texts)
        parts.extend(t.get_text() for t in ax.get_xticklabels())
        parts.extend(t.get_text() for t in ax.get_yticklabels())
    return "\n".join(parts)


def test_v05_v06_heatmap_lab_figure():
    story = (ROOT / "demos" / "cmapss" / "story_fd001.m").read_text()
    assert "heatmap(" in story
    assert "imagesc" not in story

    session = Session.create_default()
    repl = ReplSession(session)
    repl.run_line(f'run("{(ROOT / "demos" / "cmapss" / "story_fd001.m").as_posix()}");')

    names = _texts(session.workspace.get("metric_names"))
    chart = session.workspace.get("hm")
    assert chart.get_prop("ColorbarVisible").text == "on"
    cd = np.asarray(chart.get_prop("ColorData").backend_buffer(), float)
    np.testing.assert_allclose(cd, np.asarray(session.workspace.get("C").backend_buffer(), float))
    assert _texts(chart.get_prop("XDisplayLabels")) == names
    assert _texts(chart.get_prop("YDisplayLabels")) == names
    assert np.allclose(np.asarray(chart.get_prop("ColorLimits").backend_buffer()).reshape(-1), [-1, 1])

    model = session.plots._gmodel
    layouts = [c for fig in model.figures() for c in fig.children if c.alive and c.type == "tiledlayout"]
    assert len(layouts) == 1
    assert list(layouts[0].props["GridSize"]) == [2.0, 3.0]
    note = layouts[0].props["XLabel"].props["String"]
    assert "Saxena" in note and DOI in note
    assert "PHM08" in note

    gfx = session.graphics
    figs = [fig for fig in gfx._figures if fig is not None]
    assert len(figs) == 2
    lab, v03 = figs
    assert "smoothdata" in (v03.axes[0].get_title() or "")
    assert len(v03.axes[0].lines) == 3

    blob = _rendered_text(lab)
    assert "unit 1" in blob
    assert "Saxena" in blob and DOI in blob
    assert "sensor traces" in blob
    assert "cycle" in blob and "z-score" in blob

    traces = _axes_titled(lab, "sensor traces")
    assert len(traces.lines) == int(_scalar(session, "nshow")) == 4
    early = _axes_titled(lab, "early vs late")
    assert len(early.lines) == 2
    corr = _axes_titled(lab, "correlation")
    assert corr.images
    np.testing.assert_allclose(np.asarray(corr.images[0].get_array(), float), cd)
    assert [t.get_text() for t in corr.get_xticklabels()] == names
    assert [t.get_text() for t in corr.get_yticklabels()] == names
    assert "sensor_9" in names and "sensor_14" in names
    im = corr.images[0]
    assert im.colorbar is not None
    assert im.norm.vmin == -1 and im.norm.vmax == 1
    fail = _axes_titled(lab, "failure cycles")
    assert fail.containers
    rul = _axes_titled(lab, "train RUL")
    assert len(rul.lines) == 1
    assert _scalar(session, "unit_id") == 1
