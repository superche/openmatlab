"""M14 V01/V02: Zenodo download of FD001 and the public train scale (Epic #994).

The zip is fetched into downloads/cmapss/ (gitignored). This test needs the network
only when that cache is empty or the hash does not match the manifest.
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


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def test_v01_v02_fd001_download_and_readtable():
    out = cmapss.fetch()
    meta = cmapss.load_manifest()
    zpath = cmapss.cache_dir() / meta["zip_name"]
    cmapss.verify_zip(zpath, meta)
    for spec in meta["fd001"].values():
        assert (out / spec["file"]).is_file()
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
    assert _scalar(session, "w") == 26
    assert _scalar(session, "u") == 100
    assert _scalar(session, "n1") == 192
    assert session.workspace.get("T").names == list(cmapss.column_names())

    repl.run_line("Te = load_fd001('test'); R = load_fd001('rul'); ht = height(Te); ut = numel(unique(Te.unit)); hr = height(R);")
    assert _scalar(session, "ht") == 13096
    assert _scalar(session, "ut") == 100
    assert _scalar(session, "hr") == 100
    assert session.workspace.get("R").names == ["rul"]
