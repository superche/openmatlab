"""C-MAPSS FD001 fetch manifest and space-delimited readtable path (Epic #994)."""

from __future__ import annotations

import subprocess
import zipfile

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs import cmapss
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()
DEMO = ROOT / "demos" / "cmapss"


def _num(session, name):
    return np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def test_manifest_pins_zenodo_and_phm08_names():
    meta = cmapss.load_manifest()
    assert meta["url"] == "https://zenodo.org/records/15346912/files/CMAPSSData.zip?download=1"
    assert meta["doi"] == "10.5281/zenodo.15346912"
    assert meta["license"] == "CC-BY-4.0"
    assert meta["bytes"] == 12425978
    assert len(meta["sha256"]) == 64
    names = cmapss.column_names()
    assert names[:5] == ("unit", "cycle", "setting_1", "setting_2", "setting_3")
    assert names[-1] == "sensor_21" and len(names) == 26
    assert meta["fd001"]["train"]["rows"] == 20631
    assert meta["fd001"]["train"]["units"] == 100


def test_cache_path_is_gitignored():
    for rel in ("downloads/cmapss/CMAPSSData.zip", "downloads/cmapss/fd001/train_FD001.txt"):
        ignored = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT)
        assert ignored.returncode == 0, rel
    tracked = subprocess.run(["git", "ls-files", "downloads/cmapss"], cwd=ROOT, capture_output=True, text=True)
    assert tracked.stdout.strip() == ""


def test_verify_zip_rejects_a_different_file(tmp_path):
    bogus = tmp_path / "CMAPSSData.zip"
    bogus.write_bytes(b"not the nasa archive")
    with pytest.raises(RuntimeError, match="size|sha256"):
        cmapss.verify_zip(bogus)


def test_extract_fd001_keeps_only_the_three_files(tmp_path):
    zpath = tmp_path / "CMAPSSData.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("train_FD001.txt", "1 1\n")
        zf.writestr("nested/test_FD001.txt", "2 2\n")
        zf.writestr("RUL_FD001.txt", "9\n")
        zf.writestr("../evil.txt", "nope")
        zf.writestr("train_FD002.txt", "skip\n")
    dest = tmp_path / "fd001"
    cmapss.extract_fd001(zpath, dest)
    assert (dest / "train_FD001.txt").read_text(encoding="utf-8") == "1 1\n"
    assert (dest / "test_FD001.txt").read_text(encoding="utf-8") == "2 2\n"
    assert (dest / "RUL_FD001.txt").read_text(encoding="utf-8") == "9\n"
    assert not (dest / "train_FD002.txt").exists()
    assert not (dest / "evil.txt").exists()
    assert not (tmp_path / "evil.txt").exists()


def test_space_padded_readtable_and_readmatrix(tmp_path):
    """No header, repeated spaces, trailing space: 26 PHM08 columns."""
    row = "1  1  -0.0007 -0.0004  100.0  " + " ".join(str(i) for i in range(1, 22)) + "  \n"
    row2 = "1  2  -0.0007 -0.0004  100.0  " + " ".join(str(i) for i in range(1, 22)) + "  \n"
    path = tmp_path / "mini_FD001.txt"
    path.write_text(row + row2, encoding="utf-8")
    session = Session.create_default()
    repl = ReplSession(session)
    posix = path.as_posix()
    repl.run_line(
        f"T = readtable('{posix}', 'Delimiter', ' ', 'ReadVariableNames', false, 'VariableNames', cmapss_names());"
        "h = height(T); w = width(T); u = T.unit'; s = T.sensor_21';"
        f"M = readmatrix('{posix}', 'Delimiter', 'space');"
    )
    table = session.workspace.get("T")
    assert table.names == list(cmapss.column_names())
    assert _num(session, "h") == [2.0]
    assert _num(session, "w") == [26.0]
    assert _num(session, "u") == [1.0, 1.0]
    assert _num(session, "s") == [21.0, 21.0]
    assert np.asarray(session.workspace.get("M").backend_buffer()).shape == (2, 26)


def test_load_fd001_rejects_an_unknown_split_before_download():
    session = Session.create_default()
    repl = ReplSession(session)
    repl.run_line(f'addpath("{DEMO.as_posix()}");')
    with pytest.raises(EvalError, match="train, test, or rul"):
        repl.run_line("load_fd001('nope');")
