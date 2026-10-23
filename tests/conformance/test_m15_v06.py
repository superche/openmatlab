"""M15 V06: one 2-by-2 tiledlayout for record 100 (Epic #1011).

The story still ends on the raw-versus-filtered axes. This test checks the
lab figure created before that one. The PhysioNet files stay in the gitignored
cache.
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()
DOI = "10.13026/C2F305"


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def _col(session, name) -> np.ndarray:
    return np.asarray(session.workspace.get(name).backend_buffer(), dtype=float).reshape(-1)


def _rendered(fig) -> str:
    parts = []
    sup = getattr(fig, "_suptitle", None)
    if sup is not None:
        parts.append(sup.get_text())
    parts.extend(t.get_text() for t in fig.texts)
    for ax in fig.axes:
        parts.append(ax.get_title() or "")
        parts.append(ax.get_xlabel() or "")
        parts.append(ax.get_ylabel() or "")
    return "\n".join(parts)


def test_v06_record100_tiled_lab_figure():
    ignored = subprocess.run(["git", "check-ignore", "-q", "downloads/mitbih/100.dat"], cwd=ROOT)
    assert ignored.returncode == 0

    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "mitbih" / "story_record100.m"
    repl.run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "nlines") == 2
    assert _scalar(session, "agree") == 0.0
    assert _col(session, "gs").tolist() == [2.0, 2.0]
    assert _scalar(session, "ntiles") == 4
    assert _scalar(session, "npeaks") > 0

    model = session.plots._gmodel
    layouts = [c for fig in model.figures() for c in fig.children if c.alive and c.type == "tiledlayout"]
    assert len(layouts) == 1
    assert list(layouts[0].props["GridSize"]) == [2.0, 2.0]
    note = layouts[0].props["XLabel"].props["String"]
    assert DOI in note
    assert "Moody" in note and "Mark" in note and "2001" in note
    assert "Goldberger" in note and "2000" in note
    assert layouts[0].props["Title"].props["String"] == "MIT-BIH record 100"

    gfx = session.graphics
    figs = [fig for fig in gfx._figures if fig is not None]
    lab = next(fig for fig in figs if len(fig.axes) >= 4)
    last = gfx.last_figure
    assert last is not lab
    assert len(last.axes[0].lines) == 2
    assert "100" in (last.axes[0].get_title() or "") and "MLII" in (last.axes[0].get_title() or "")

    blob = _rendered(lab)
    assert "record 100" in blob
    assert DOI in blob and "Moody" in blob and "Goldberger" in blob
    assert "raw" in blob and "R peaks" in blob and "RR" in blob and "spectrum" in blob
    assert "\ns\n" in f"\n{blob}\n" or any((ax.get_xlabel() or "") == "s" for ax in lab.axes)
    labels = {(ax.get_xlabel() or "") for ax in lab.axes} | {(ax.get_ylabel() or "") for ax in lab.axes}
    assert "s" in labels and "mV" in labels and "Hz" in labels

    raw = next(ax for ax in lab.axes if "raw" in (ax.get_title() or ""))
    peaks = next(ax for ax in lab.axes if "R peaks" in (ax.get_title() or ""))
    rr = next(ax for ax in lab.axes if "RR" in (ax.get_title() or ""))
    spec = next(ax for ax in lab.axes if "spectrum" in (ax.get_title() or ""))
    assert len(raw.lines) == 1
    assert len(peaks.lines) == 2
    assert rr.containers
    assert len(spec.lines) == 1
    assert spec.get_xlim() == pytest.approx((0, 60))
    assert np.allclose(np.asarray(raw.lines[0].get_ydata(), dtype=float), _col(session, "xshow"))
    assert np.allclose(np.asarray(peaks.lines[0].get_ydata(), dtype=float), _col(session, "yshow"))
