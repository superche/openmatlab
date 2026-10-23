"""M15 V03: zero-phase 0.5–40 Hz bandpass on record 100 MLII (Epic #1009).

Uses the cache filled by ``mitbih_fetch`` (gitignored). Network is required
only when that cache is empty or a hash does not match the manifest.
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


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def _col(session, name) -> np.ndarray:
    return np.asarray(session.workspace.get(name).backend_buffer(), dtype=float).reshape(-1)


def test_v03_record100_bandpass_shares_axes():
    ignored = subprocess.run(["git", "check-ignore", "-q", "downloads/mitbih/100.dat"], cwd=ROOT)
    assert ignored.returncode == 0
    tracked = subprocess.run(["git", "ls-files", "downloads/mitbih"], cwd=ROOT, capture_output=True, text=True)
    assert tracked.stdout.strip() == ""

    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "mitbih" / "story_record100.m"
    repl.run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "fs") == 360
    assert _scalar(session, "nch") == 2
    assert _scalar(session, "ns") == 650000
    assert _scalar(session, "s0") == pytest.approx(-0.145)
    assert _scalar(session, "f1") == 0.5
    assert _scalar(session, "f2") == 40
    assert _scalar(session, "order") == 2
    assert _scalar(session, "nlines") == 2
    assert _scalar(session, "agree") == 0.0
    assert _scalar(session, "nshow") == 3600

    y = _col(session, "y")
    x = _col(session, "x")
    assert y.shape == (650000,)
    assert x.shape == (650000,)
    assert np.isfinite(y).all()
    assert abs(float(np.mean(y))) < 0.02
    assert 0.05 < float(np.std(x)) < 1.0
    assert 0.05 < float(np.std(y)) < 1.0
    assert float(np.max(np.abs(_col(session, "xshow") - _col(session, "yshow")))) > 0.01

    gfx = session.graphics
    assert gfx is not None and gfx.last_figure is not None
    lines = gfx.last_figure.axes[0].lines
    assert len(lines) == 2
    t = _col(session, "t")
    for line, series in zip(lines, (_col(session, "xshow"), _col(session, "yshow"))):
        assert np.allclose(np.asarray(line.get_xdata(), dtype=float), t)
        assert np.allclose(np.asarray(line.get_ydata(), dtype=float), series)
    title = gfx.last_figure.axes[0].get_title()
    assert "100" in title and "MLII" in title
