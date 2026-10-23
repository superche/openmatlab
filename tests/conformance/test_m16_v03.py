"""M16 V03: global imbinarize and bwareaopen on one BBBC038 FOV (Epic #1021).

Uses the cache filled by ``bbbc038_fetch`` (gitignored). Network is required
only when that cache is empty or a hash does not match the manifest.
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


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def test_v03_imbinarize_bwareaopen_before_after_panel():
    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "bbbc038" / "story_stage1_test.m"
    repl.run_line(f'run("{story.as_posix()}");')

    assert _scalar(session, "h") == 256
    assert _scalar(session, "w") == 256
    assert _scalar(session, "c") == 3
    assert _scalar(session, "nbytes") == 9545388
    assert session.workspace.get("cls").text == "uint8"
    assert _scalar(session, "level") == pytest.approx(22 / 255)
    assert _scalar(session, "minarea") == 50
    assert _scalar(session, "nraw") == 1003
    assert _scalar(session, "nopen") == 978
    assert session.workspace.get("bwcls").text == "logical"
    assert _scalar(session, "ntiles") == 2

    raw = np.asarray(session.workspace.get("I").backend_buffer())
    mask = np.asarray(session.workspace.get("BW2").backend_buffer())
    assert raw.shape == (256, 256, 3) and raw.dtype == np.uint8
    assert mask.shape == (256, 256) and mask.dtype == np.bool_
    assert int(mask.sum()) == 978

    model = gb.model(session)
    fig = model.gcf()
    layouts = [c for c in fig.children if c.alive and c.type == "tiledlayout"]
    assert len(layouts) == 1
    assert list(layouts[0].props["GridSize"]) == [1.0, 2.0]
    tiles = [
        c for c in fig.children if c.alive and c.type == "axes" and getattr(c, "layout", None) is layouts[0]
    ]
    assert sorted(a.tile for a in tiles) == [1, 2]
    by_tile = {a.tile: a for a in tiles}
    assert by_tile[1].props["Title"].props["String"] == "BBBC038 raw"
    assert by_tile[2].props["Title"].props["String"] == "BBBC038 mask"
    for axes in tiles:
        assert axes.props["YDir"] == "reverse"
        assert axes.props["DataAspectRatio"] == [1.0, 1.0, 1.0]
        images = [c for c in axes.children if c.alive and c.type == "image"]
        assert len(images) == 1
    raw_cd = np.asarray(by_tile[1].children[-1].props["CData"], dtype=float)
    mask_cd = np.asarray(by_tile[2].children[-1].props["CData"], dtype=float)
    assert raw_cd.shape == (256, 256, 3)
    assert np.allclose(raw_cd, raw.astype(float) / 255.0)
    assert mask_cd.shape == (256, 256, 3)
    assert np.allclose(mask_cd[..., 0], mask.astype(float))
    assert np.allclose(mask_cd[..., 0], mask_cd[..., 1])
    assert np.allclose(mask_cd[..., 1], mask_cd[..., 2])
