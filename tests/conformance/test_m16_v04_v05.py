"""M16 V04/V05: nucleus count and area morphology on one BBBC038 FOV (Epic #1022).

``stage1_test`` contains images only, so there is no mask file to score
against. The count is ``bwlabel`` / ``bwconncomp`` of the I-E2 mask
(8-connected, area at least 50). Tolerance on the count and the areas is 0.
Eccentricity must match the second-central-moment formula below.
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs import graphics_builtins as gb
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()
AREAS = [152.0, 219.0, 143.0, 117.0, 193.0, 154.0]


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def _vec(session, name) -> np.ndarray:
    return np.asarray(session.workspace.get(name).backend_buffer(), dtype=float).reshape(-1)


def _eccentricity(rows: np.ndarray, cols: np.ndarray) -> float:
    """Same formula as docs/design/EPIC-1022-regionprops.md. Rows and cols are 0-based."""
    if rows.size <= 1:
        return 0.0
    y = rows.astype(float) - rows.astype(float).mean()
    x = cols.astype(float) - cols.astype(float).mean()
    m20 = float(np.sum(x * x))
    m02 = float(np.sum(y * y))
    m11 = float(np.sum(x * y))
    delta = float(np.sqrt((m20 - m02) ** 2 + 4.0 * m11 * m11))
    major = (m20 + m02 + delta) / 2.0
    minor = (m20 + m02 - delta) / 2.0
    if major <= 0.0:
        return 0.0
    ratio = 0.0 if minor <= 0.0 else minor / major
    return float(np.sqrt(max(0.0, 1.0 - ratio)))


def test_v04_v05_count_and_area_histogram():
    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "bbbc038" / "story_stage1_test.m"
    repl.run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "h") == 256
    assert _scalar(session, "nbytes") == 9545388
    assert _scalar(session, "level") == pytest.approx(22 / 255)
    assert _scalar(session, "minarea") == 50
    assert _scalar(session, "nopen") == 978
    assert _scalar(session, "ntiles") == 2
    assert _scalar(session, "ncount") == 6
    assert _scalar(session, "ncc") == 6
    areas = _vec(session, "areas")
    assert areas.tolist() == AREAS
    assert float(areas.sum()) == 978
    assert _scalar(session, "meanarea") == 163
    assert _scalar(session, "medarea") == 153

    labels = np.asarray(session.workspace.get("L").backend_buffer())
    ecc = _vec(session, "ecc")
    for lab, area, one in zip(range(1, 7), AREAS, ecc):
        rows, cols = np.nonzero(labels == lab)
        assert rows.size == area
        assert one == pytest.approx(_eccentricity(rows, cols), abs=1e-9)
        centroid = np.asarray(session.workspace.get("stats").get("Centroid", lab - 1).backend_buffer()).reshape(-1)
        assert centroid[0] == pytest.approx(float(cols.mean() + 1.0))
        assert centroid[1] == pytest.approx(float(rows.mean() + 1.0))
    assert _scalar(session, "meanecc") == pytest.approx(float(ecc.mean()))

    model = gb.model(session)
    current = model.gcf()
    layouts = [c for c in current.children if c.alive and c.type == "tiledlayout"]
    assert len(layouts) == 1
    assert list(layouts[0].props["GridSize"]) == [1.0, 2.0]
    hist_figs = [f for f in model.figures() if f is not current]
    assert len(hist_figs) == 1
    axes = [c for c in hist_figs[0].children if c.alive and c.type == "axes"]
    assert len(axes) == 1
    assert axes[0].props["Title"].props["String"] == "BBBC038 areas"
    histograms = [c for c in axes[0].children if c.alive and c.type == "histogram"]
    assert len(histograms) == 1
    assert np.allclose(np.asarray(histograms[0].props["Data"], dtype=float), areas)
