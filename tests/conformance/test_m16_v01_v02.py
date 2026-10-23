"""M16 V01/V02: Broad stage1_test.zip download and imread of one FOV (Epic #1020).

The zip and the PNG land in downloads/bbbc038/ (gitignored). This test needs
the network only when that cache is empty or a hash does not match the manifest.
Pixel values were cross-checked with Pillow on the same PNG bytes: RGB at
(0, 0) is [3, 3, 3] and at (128, 128) is [6, 6, 6]. Alpha on this FOV is 255.
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs import bbbc038
from openmatlab.libs.imread import decode_png
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def test_v01_v02_stage1_test_download_and_imread():
    cache = bbbc038.fetch()
    meta = bbbc038.load_manifest()
    bbbc038.verify_zip(cache.zip_path, meta)
    assert cache.nbytes == 9545388
    bbbc038.verify_cached(
        cache.image, {"name": cache.image.name, "bytes": meta["fov"]["bytes"], "sha256": meta["fov"]["sha256"]}
    )
    for rel in (f"downloads/bbbc038/{cache.zip_path.name}", f"downloads/bbbc038/fov/{cache.image.name}"):
        ignored = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT)
        assert ignored.returncode == 0, rel
    tracked = subprocess.run(["git", "ls-files", "downloads/bbbc038"], cwd=ROOT, capture_output=True, text=True)
    assert tracked.stdout.strip() == ""

    image, alpha = decode_png(cache.image.read_bytes())
    assert image.shape == (meta["fov"]["height"], meta["fov"]["width"], 3)
    assert image.dtype == np.uint8
    assert image[0, 0].tolist() == [3, 3, 3]
    assert image[128, 128].tolist() == [6, 6, 6]
    assert alpha is not None and alpha.shape == (256, 256)
    assert int(alpha.min()) == 255 and int(alpha.max()) == 255

    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "bbbc038" / "story_stage1_test.m"
    repl.run_line(f'run("{story.as_posix()}");')
    assert _scalar(session, "h") == 256
    assert _scalar(session, "w") == 256
    assert _scalar(session, "c") == 3
    assert _scalar(session, "nbytes") == 9545388
    assert session.workspace.get("cls").text == "uint8"
    assert session.workspace.get("zpath").text.endswith("stage1_test.zip")
    assert session.workspace.get("ipath").text.endswith(cache.image.name)
