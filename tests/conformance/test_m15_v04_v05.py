"""M15 V04/V05: R peaks, RR histogram, and an amplitude spectrum (Epic #1010).

Uses the cache filled by the story's ``mitbih_fetch`` (gitignored). Network
is required only when that cache is empty or a hash does not match.
The window check is a fixed local-maximum rule, not the ``.atr`` file.
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


def _formula_peaks(y: np.ndarray, height: float, min_dist: float) -> np.ndarray:
    """1-based indices. A run is a peak when it is strictly above both neighbors."""
    change = np.flatnonzero(y[1:] != y[:-1]) + 1
    starts = np.concatenate((np.array([0], dtype=int), change))
    ends = np.concatenate((change, np.array([y.size], dtype=int)))
    s = starts[1:-1]
    e = ends[1:-1]
    vals = y[s]
    idx = s[(vals > y[s - 1]) & (vals > y[e]) & (vals >= height)]
    taken = np.zeros(y.size, dtype=bool)
    order = np.lexsort((idx, -y[idx]))
    keep = []
    for k in order:
        i = int(idx[k])
        if taken[i]:
            continue
        keep.append(i)
        lo = max(0, int(np.floor(i - min_dist)) + 1)
        hi = min(y.size - 1, int(np.ceil(i + min_dist)) - 1)
        taken[lo : hi + 1] = True
    return np.asarray(sorted(keep), dtype=float) + 1.0


def test_v04_v05_peaks_rr_and_spectrum():
    ignored = subprocess.run(["git", "check-ignore", "-q", "downloads/mitbih/100.dat"], cwd=ROOT)
    assert ignored.returncode == 0
    tracked = subprocess.run(["git", "ls-files", "downloads/mitbih"], cwd=ROOT, capture_output=True, text=True)
    assert tracked.stdout.strip() == ""

    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "mitbih" / "story_record100.m"
    repl.run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "fs") == 360
    assert _scalar(session, "nlines") == 2
    assert _scalar(session, "agree") == 0.0
    assert _scalar(session, "height") == 0.5
    assert _scalar(session, "mindist") == 90
    assert _scalar(session, "npeak_lines") == 2

    locs = _col(session, "locs")
    pks = _col(session, "pks")
    rr = _col(session, "rr")
    assert locs.size == pks.size
    assert _scalar(session, "npeaks") == locs.size
    assert rr.size == locs.size - 1
    assert np.all(np.diff(locs) >= 90)
    assert 2000 <= locs.size <= 2500
    assert 0.7 < _scalar(session, "mean_rr") < 0.9
    assert float(rr.min()) >= 0.25
    assert float(rr.max()) < 2.0
    assert 8 <= _scalar(session, "npeaks_win") <= 20
    assert np.all(pks >= 0.5)

    y = _col(session, "y")
    yshow = _col(session, "yshow")
    window = locs[locs <= yshow.size]
    formula = _formula_peaks(y, 0.5, 90)
    formula = formula[formula <= yshow.size]
    # The demo window is the gate: within 2 samples of the fixed rule.
    assert window.size == formula.size
    assert np.max(np.abs(window - formula)) <= 2

    spec = np.abs(np.fft.fft(yshow))
    spec[0] = 0
    nh = int(_scalar(session, "nh"))
    expect = int(np.argmax(spec[:nh]))
    assert _scalar(session, "fft_bin") == expect + 1
    assert _scalar(session, "fpeak") == pytest.approx(expect * 360 / yshow.size)
    assert 0 < _scalar(session, "fpeak") < 40
    assert _scalar(session, "fft_mag") == pytest.approx(spec[expect])

    gfx = session.graphics
    assert gfx is not None
    titles = [fig.axes[0].get_title() for fig in gfx._figures if fig is not None and fig.axes]
    assert any("R peaks" in t for t in titles)
    assert any("RR" in t for t in titles)
    assert any("spectrum" in t for t in titles)
    assert "100" in titles[-1] and "MLII" in titles[-1]
    peak_fig = next(fig for fig in gfx._figures if fig is not None and "R peaks" in fig.axes[0].get_title())
    assert len(peak_fig.axes[0].lines) == 2
    hist_fig = next(fig for fig in gfx._figures if fig is not None and "RR" in fig.axes[0].get_title())
    assert hist_fig.axes[0].containers
    spec_fig = next(fig for fig in gfx._figures if fig is not None and "spectrum" in fig.axes[0].get_title())
    assert spec_fig.axes[0].get_xlim() == pytest.approx((0, 60))
    assert len(spec_fig.axes[0].lines) == 1
