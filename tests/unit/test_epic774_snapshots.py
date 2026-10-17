"""Epic #774 (M13 G-E7, G10): golden snapshot scenes, deterministic rendering, tolerance."""

from __future__ import annotations

import pytest

from openmatlab.qa import snapshots

pytestmark = [pytest.mark.unit, pytest.mark.needs_matplotlib]


def test_at_least_40_scenes():
    assert len(snapshots.scenes()) >= 40
    assert len({s.name for s in snapshots.scenes()}) == len(snapshots.scenes())


def test_all_scenes_within_tolerance(tmp_path):
    res = snapshots.check_all(tmp_path)
    assert all(r.ok for r in res), [(r.name, r.detail) for r in res if not r.ok]
    assert all((tmp_path / f"{r.name}.png").is_file() for r in res)


def test_deterministic_digests(tmp_path):
    a = snapshots.check_all(tmp_path / "a")
    b = snapshots.check_all(tmp_path / "b")
    assert [r.digest for r in a] == [r.digest for r in b]
    assert all(len(r.digest) == 64 for r in a)


def test_tolerance_helpers():
    import numpy as np
    x = np.zeros((16, 16, 3))
    y = x.copy()
    y[0, 0] = [1, 0, 0]  # one far pixel out of 256 -> 0.39 % < 1 %
    ok, detail = snapshots.within_tolerance(x, y)
    assert ok and "deltaE_frac" in detail
    z = np.ones((16, 16, 3))
    ok2, _ = snapshots.within_tolerance(x, z)
    assert not ok2 or snapshots.ssim(x, z) >= snapshots.SSIM_MIN
