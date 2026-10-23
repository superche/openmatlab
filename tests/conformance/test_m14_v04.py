"""M14 V04: FD001 early/late means, correlation, and train RUL (Epic #996).

Goldens are the fixed formulas in this file (groupsummary mean, sample Pearson,
RUL = max(cycle) - cycle). The zip stays in the gitignored cache. Network is
required only when that cache is empty or the hash does not match the manifest.

The single-channel fft line is the demo bonus. It is checked here so the
printed number stays honest; it is not part of the V04 gate.
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs import cmapss
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()
W = 30
THRESH = 1e-6
RTOL = 1e-8
ATOL = 1e-8


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def _arr(session, name) -> np.ndarray:
    return np.asarray(session.workspace.get(name).backend_buffer(), dtype=float)


def _cell_texts(value) -> list[str]:
    return [item.text for row in value.rows for item in row]


def pearson(columns: np.ndarray) -> np.ndarray:
    """Sample Pearson correlation. Covariance divides by n-1. Diagonal is 1."""
    x = np.asarray(columns, dtype=float)
    xc = x - x.mean(axis=0, keepdims=True)
    cov = (xc.T @ xc) / (x.shape[0] - 1)
    scale = np.sqrt(np.diag(cov))
    out = cov / np.outer(scale, scale)
    np.fill_diagonal(out, 1.0)
    return out


def reference(data: np.ndarray) -> dict:
    """Per-unit window means, train RUL, and sensor correlation. No engine calls."""
    unit = data[:, 0]
    cycle = data[:, 1]
    sensors = data[:, 5:]
    keep = sensors.std(axis=0, ddof=1) > THRESH
    kept = sensors[:, keep]
    units = np.unique(unit)
    fails = np.empty(units.size)
    early = np.empty((units.size, int(keep.sum())))
    late = np.empty_like(early)
    rul = np.empty(unit.size)
    for i, u in enumerate(units):
        mask = unit == u
        cyc = cycle[mask]
        fail = float(cyc.max())
        fails[i] = fail
        block = kept[mask]
        early[i] = block[cyc <= W].mean(axis=0)
        late[i] = block[cyc > fail - W].mean(axis=0)
        rul[mask] = fail - cyc
    delta = late - early
    return {
        "keep": keep,
        "units": units,
        "fail": fails,
        "early": early,
        "late": late,
        "delta": delta,
        "rul": rul,
        "corr": pearson(kept),
        "fleet_early": early.mean(axis=0),
        "fleet_late": late.mean(axis=0),
        "fleet_delta": delta.mean(axis=0),
    }


def _axes_titled(fig, fragment: str):
    hits = [ax for ax in fig.axes if fragment in (ax.get_title() or "")]
    assert hits, f"no axes titled with {fragment!r}"
    return hits[0]


def test_v04_fd001_metrics_match_the_formula():
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "downloads/cmapss/CMAPSSData.zip"],
        cwd=ROOT,
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(["git", "ls-files", "downloads"], cwd=ROOT, capture_output=True, text=True)
    assert "CMAPSSData.zip" not in tracked.stdout
    assert "train_FD001.txt" not in tracked.stdout

    data = np.loadtxt(cmapss.fetch() / "train_FD001.txt")
    ref = reference(data)
    names = list(cmapss.column_names()[5:])
    kept = [name for name, flag in zip(names, ref["keep"]) if flag]

    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "cmapss" / "story_fd001.m"
    repl.run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "h") == 20631
    assert _scalar(session, "W") == W
    # Unit 1 drops sensor_6 (numerical dust on that unit). Across the fleet its
    # sample std is well above 1e-6, so the metric table keeps it.
    assert _scalar(session, "same_drop") == 0
    assert "sensor_6" in kept
    assert _cell_texts(session.workspace.get("metric_names")) == kept
    assert _arr(session, "units").reshape(-1).tolist() == ref["units"].tolist()
    np.testing.assert_allclose(_arr(session, "fc").reshape(-1), ref["fail"], rtol=0, atol=0)
    np.testing.assert_allclose(_arr(session, "rul").reshape(-1), ref["rul"], rtol=0, atol=0)
    assert _scalar(session, "n_rul0") == ref["units"].size
    assert np.count_nonzero(ref["rul"] == 0) == ref["units"].size
    np.testing.assert_allclose(_arr(session, "early_m"), ref["early"], rtol=RTOL, atol=ATOL)
    np.testing.assert_allclose(_arr(session, "late_m"), ref["late"], rtol=RTOL, atol=ATOL)
    np.testing.assert_allclose(_arr(session, "delta"), ref["delta"], rtol=RTOL, atol=ATOL)
    np.testing.assert_allclose(_arr(session, "fleet_early").reshape(-1), ref["fleet_early"], rtol=RTOL, atol=ATOL)
    np.testing.assert_allclose(_arr(session, "fleet_late").reshape(-1), ref["fleet_late"], rtol=RTOL, atol=ATOL)
    np.testing.assert_allclose(_arr(session, "fleet_delta").reshape(-1), ref["fleet_delta"], rtol=RTOL, atol=ATOL)
    np.testing.assert_allclose(_arr(session, "C"), ref["corr"], rtol=RTOL, atol=ATOL)

    off = ref["corr"].copy()
    np.fill_diagonal(off, -np.inf)
    lin = int(np.argmax(off.ravel(order="F")))
    assert _scalar(session, "corr_i") == (lin % off.shape[0]) + 1
    assert _scalar(session, "corr_j") == (lin // off.shape[0]) + 1
    np.testing.assert_allclose(_scalar(session, "corr_offmax"), off.ravel(order="F")[lin], rtol=RTOL, atol=ATOL)

    # Unit 1 window traces of the channel V03 plots (sensor_4).
    u1 = data[data[:, 0] == 1]
    picked = names.index("sensor_4")
    series = u1[:, 5 + picked]
    cyc = u1[:, 1]
    np.testing.assert_allclose(_arr(session, "early_y").reshape(-1), series[cyc <= W], rtol=RTOL, atol=ATOL)
    np.testing.assert_allclose(_arr(session, "late_y").reshape(-1), series[cyc > cyc.max() - W], rtol=RTOL, atol=ATOL)
    assert _arr(session, "early_y").size == W
    assert _arr(session, "late_y").size == W

    gfx = session.graphics
    assert gfx is not None and gfx.last_figure is not None
    figs = [fig for fig in gfx._figures if fig is not None]
    assert len(figs) == 2
    assert gfx.last_figure is figs[-1]
    # The last figure is still the V03 raw/smoothdata axes.
    v03 = gfx.last_figure.axes[0]
    assert len(v03.lines) == 3
    assert "unit 1" in v03.get_title()
    assert "smoothdata" in v03.get_title()

    metrics = figs[0]
    early_ax = _axes_titled(metrics, "early vs late")
    assert len(early_ax.lines) == 2
    np.testing.assert_allclose(np.asarray(early_ax.lines[0].get_ydata(), float), _arr(session, "early_y").reshape(-1))
    np.testing.assert_allclose(np.asarray(early_ax.lines[1].get_ydata(), float), _arr(session, "late_y").reshape(-1))
    corr_ax = _axes_titled(metrics, "correlation")
    assert corr_ax.images
    np.testing.assert_allclose(np.asarray(corr_ax.images[0].get_array(), float), _arr(session, "C"), rtol=RTOL, atol=ATOL)
    fail_ax = _axes_titled(metrics, "failure cycles")
    heights = [float(bar.get_height()) for cont in fail_ax.containers for bar in cont]
    assert sum(heights) == ref["units"].size
    rul_ax = _axes_titled(metrics, "train RUL")
    assert len(rul_ax.lines) == 1
    np.testing.assert_allclose(np.asarray(rul_ax.lines[0].get_ydata(), float), _arr(session, "rul_u1").reshape(-1))

    # Bonus, not a V04 gate: one fft of the unit-1 channel, DC removed.
    spec = np.abs(np.fft.fft(_arr(session, "raw").reshape(-1)))
    spec[0] = 0
    half = spec[: spec.size // 2 + 1]
    assert _scalar(session, "fft_bin") == int(np.argmax(half)) + 1
    np.testing.assert_allclose(_scalar(session, "fft_mag"), float(half.max()), rtol=RTOL, atol=ATOL)
