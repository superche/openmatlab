"""M14 V03: drop near-constant FD001 sensors and smooth one unit (Epic #995).

Uses the cache filled by ``load_fd001`` (gitignored). Network is required only
when that cache is empty or the zip hash does not match the manifest.
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
DROPPED = (
    "sensor_1",
    "sensor_5",
    "sensor_6",
    "sensor_10",
    "sensor_16",
    "sensor_18",
    "sensor_19",
)


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def _col(session, name) -> np.ndarray:
    return np.asarray(session.workspace.get(name).backend_buffer(), dtype=float).reshape(-1)


def _cell_texts(value) -> list[str]:
    return [item.text for row in value.rows for item in row]


def test_v03_unit1_smooth_and_dual_line():
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "downloads/cmapss/CMAPSSData.zip"],
        cwd=ROOT,
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(["git", "ls-files", "downloads"], cwd=ROOT, capture_output=True, text=True)
    assert "CMAPSSData.zip" not in tracked.stdout
    assert "train_FD001.txt" not in tracked.stdout

    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "cmapss" / "story_fd001.m"
    repl.run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "h") == 20631
    assert _scalar(session, "n1") == 192
    assert _scalar(session, "unit_id") == 1
    assert _scalar(session, "win") == 15
    assert _scalar(session, "ndrop") == 7
    assert _scalar(session, "nkeep") == 14
    assert _cell_texts(session.workspace.get("dropped")) == list(DROPPED)
    assert session.workspace.get("picked").text == "sensor_4"
    # Idle FD001 channels sit at numerical dust; the quietest kept sensor does not.
    assert _scalar(session, "drop_max") < 1e-6
    assert _scalar(session, "keep_min") > 0.01
    assert _scalar(session, "agree") == 0
    assert _scalar(session, "sg_ok") == 1
    assert _scalar(session, "changed") == 1
    assert _scalar(session, "nlines") == 3
    assert _col(session, "raw").shape == (192,)
    assert _col(session, "sm").shape == (192,)
    assert _col(session, "sg").shape == (192,)

    gfx = session.graphics
    assert gfx is not None and gfx.last_figure is not None
    lines = gfx.last_figure.axes[0].lines
    assert len(lines) == 3
    raw, sm, sg = _col(session, "raw"), _col(session, "sm"), _col(session, "sg")
    cyc = _col(session, "cyc")
    for line, y in zip(lines, (raw, sm, sg)):
        assert np.allclose(np.asarray(line.get_xdata(), dtype=float), cyc)
        assert np.allclose(np.asarray(line.get_ydata(), dtype=float), y)
    assert "unit 1" in gfx.last_figure.axes[0].get_title()
