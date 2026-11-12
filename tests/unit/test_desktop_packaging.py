"""Release acceptance contracts for #1081 (native binaries and safe publication)."""
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys

import pytest
import yaml

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("desktop_smoke", ROOT / "packaging/smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def test_native_binary_architectures(tmp_path):
    mac = tmp_path / "mac"
    mac.write_bytes(b"\xcf\xfa\xed\xfe" + struct.pack("<I", 0x100000C))
    assert smoke.binary_arch(mac) == "arm64"
    win = tmp_path / "win"
    data = bytearray(134)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 128)
    data[128:132] = b"PE\0\0"
    struct.pack_into("<H", data, 132, 0x8664)
    win.write_bytes(data)
    assert smoke.binary_arch(win) == "x64"
    mac.write_bytes(b"\xcf\xfa\xed\xfe" + struct.pack("<I", 0x1000007))
    assert smoke.binary_arch(mac) == "other"


@pytest.mark.parametrize("signed", ["true", "false"])
def test_final_artifact_labels_and_checksums(tmp_path, signed):
    (tmp_path / "OpenMATLAB.exe").write_bytes(b"installer")
    subprocess.run([sys.executable, str(ROOT / "packaging/checksums.py"), str(tmp_path)],
                   env=dict(os.environ, SIGNED=signed), check=True)
    name = "OpenMATLAB.exe" if signed == "true" else "OpenMATLAB-unsigned.exe"
    assert (tmp_path / name).read_bytes() == b"installer"
    assert (tmp_path / (name + ".sha256")).read_text() == (
        hashlib.sha256(b"installer").hexdigest() + f"  {name}\n")


def test_release_requires_both_builds_and_tests():
    workflow = yaml.load((ROOT / ".github/workflows/desktop.yml").read_text(), Loader=yaml.BaseLoader)
    assert workflow["permissions"] == {"contents": "read"}
    publish = workflow["jobs"]["publish"]
    assert set(publish["needs"]) == {"gate", "build"}
    assert publish["if"] == "startsWith(github.ref, 'refs/tags/')"
    targets = workflow["jobs"]["build"]["strategy"]["matrix"]["include"]
    assert {(t["os"], t["arch"]) for t in targets} == {("macos-15", "arm64"), ("windows-2022", "x64")}
