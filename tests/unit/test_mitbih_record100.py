"""MIT-BIH record 100 fetch policy and format 212 reader (Epic #1008).

Synthetic headers and bytes only. The PhysioNet files are not fixtures.
"""

from __future__ import annotations

import hashlib
import subprocess

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs import mitbih
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()
DEMO = ROOT / "demos" / "mitbih"


def _pack_212(s0, s1) -> bytes:
    out = bytearray()
    for a, b in zip(s0, s1):
        a &= 0xFFF
        b &= 0xFFF
        b0 = a & 0xFF
        b2 = b & 0xFF
        b1 = ((a >> 8) & 0x0F) | (((b >> 8) & 0x0F) << 4)
        out.extend((b0, b1, b2))
    return bytes(out)


def _write_record(directory, samples, fs=360.0, resolution=11, gain=200.0, baseline=1024, units=""):
    directory.mkdir(parents=True, exist_ok=True)
    adc = np.asarray(samples, dtype=np.int32)
    (directory / "a.dat").write_bytes(_pack_212(adc[:, 0], adc[:, 1]))
    gain_field = f"{gain:g}"
    if units:
        gain_field = f"{gain:g}({resolution})/{units}"
    lines = [f"rec 2 {fs:g} {adc.shape[0]}"]
    for i, name in enumerate(("MLII", "V5")):
        if units:
            # Resolution is inside the gain token, so the next field is the baseline.
            lines.append(
                f"a.dat 212 {gain_field} {baseline} {int(adc[0, i])} {mitbih.checksum16(adc[:, i])} 0 {name}"
            )
        else:
            lines.append(
                f"a.dat 212 {gain_field} {resolution} {baseline} {int(adc[0, i])} "
                f"{mitbih.checksum16(adc[:, i])} 0 {name}"
            )
    (directory / "rec.hea").write_text("\n".join(lines) + "\n", encoding="ascii")
    return directory


def _num(session, name):
    return np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def test_manifest_pins_physionet_record_100():
    meta = mitbih.load_manifest()
    assert meta["base_url"] == "https://physionet.org/files/mitdb/1.0.0/"
    assert meta["doi"] == "10.13026/C2F305"
    assert meta["license"] == "ODC-By-1.0"
    assert meta["record"] == "100"
    assert meta["fs"] == 360
    assert meta["n_samples"] == 650000
    assert meta["n_signals"] == 2
    assert meta["format"] == 212
    assert meta["adc_resolution"] == 11
    files = {spec["name"]: spec for spec in meta["files"]}
    assert set(files) == {"100.hea", "100.dat", "100.atr"}
    assert files["100.hea"]["bytes"] == 143
    assert files["100.dat"]["bytes"] == 1950000
    assert files["100.atr"]["bytes"] == 4558
    assert all(len(spec["sha256"]) == 64 for spec in files.values())
    assert any("Moody" in line for line in meta["citations"])
    assert any("Goldberger" in line for line in meta["citations"])


def test_cache_path_is_gitignored():
    for rel in ("downloads/mitbih/100.hea", "downloads/mitbih/100.dat", "downloads/mitbih/100.atr"):
        ignored = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT)
        assert ignored.returncode == 0, rel
    tracked = subprocess.run(["git", "ls-files", "downloads/mitbih"], cwd=ROOT, capture_output=True, text=True)
    assert tracked.stdout.strip() == ""


def test_verify_cached_rejects_a_different_file(tmp_path):
    path = tmp_path / "100.hea"
    path.write_bytes(b"not the header")
    spec = {"name": "100.hea", "bytes": 143, "sha256": "ab" * 32}
    with pytest.raises(RuntimeError, match="size"):
        mitbih.verify_cached(path, spec)
    path.write_bytes(b"x" * 143)
    with pytest.raises(RuntimeError, match="sha256"):
        mitbih.verify_cached(path, spec)


def test_format_212_roundtrip_and_millivolts(tmp_path):
    """11-bit header resolution stays in a 12-bit two's-complement field, including a negative sample."""
    samples = np.array([[995, 1011], [-1, -2048]], dtype=np.int32)
    directory = _write_record(tmp_path / "rec", samples)
    rec = mitbih.load_record(directory)
    assert rec.header.fs == 360
    assert rec.header.n_samples == 2
    assert rec.header.signals[0].adc_resolution == 11
    assert rec.header.signals[0].units == "mV"
    assert np.array_equal(rec.adc, samples)
    expected = (samples.astype(np.float64) - 1024) / 200
    assert rec.sig_mv == pytest.approx(expected)
    assert rec.sig_mv[0, 0] == pytest.approx(-0.145)
    assert rec.sig_mv[0, 1] == pytest.approx(-0.065)
    assert rec.annotations == ()


def test_gain_token_can_carry_resolution_and_units(tmp_path):
    samples = np.array([[995, 1011]], dtype=np.int32)
    directory = _write_record(tmp_path / "rec", samples, units="mV")
    text = (directory / "rec.hea").read_text(encoding="ascii")
    assert "200(11)/mV" in text
    rec = mitbih.load_record(directory)
    assert rec.header.signals[0].adc_resolution == 11
    assert rec.header.signals[0].units == "mV"
    assert rec.sig_mv[0, 0] == pytest.approx(-0.145)


def test_reader_rejects_a_foreign_format_and_a_blocked_signal():
    with pytest.raises(RuntimeError, match="format 212"):
        mitbih.parse_header("rec 1 360 1\nrec.dat 16 200 11 1024 0 0 0 X\n")
    with pytest.raises(RuntimeError, match="blocked"):
        mitbih.parse_header("rec 1 360 1\nrec.dat 212 200 11 1024 0 0 8 X\n")


def test_path_escape_is_rejected_before_a_read(tmp_path):
    header = mitbih.parse_header(
        "rec 2 360 1\n../evil.dat 212 200 11 1024 0 0 0 X\n../evil.dat 212 200 11 1024 0 0 0 Y\n"
    )
    with pytest.raises(RuntimeError, match="single path segment"):
        mitbih.read_dat(tmp_path, header)
    assert not (tmp_path / "evil.dat").exists()


def test_checksum_mismatch_is_rejected(tmp_path):
    samples = np.array([[995, 1011]], dtype=np.int32)
    directory = _write_record(tmp_path / "rec", samples)
    text = (directory / "rec.hea").read_text(encoding="ascii").replace(
        f"{mitbih.checksum16(samples[:, 0])} 0 MLII", "0 0 MLII", 1
    )
    (directory / "rec.hea").write_text(text, encoding="ascii")
    with pytest.raises(RuntimeError, match="checksum"):
        mitbih.load_record(directory)


def test_atr_delta_aux_and_skip():
    # Code 1 (normal) at sample 18, no aux.
    plain = bytes((18, 1 << 2, 0, 0))
    assert mitbih.parse_atr(plain) == [mitbih.Annotation(18, 1, "")]
    # Code 28 at sample 18, aux "(N" stored with a trailing NUL and an odd-length pad.
    aux = bytes((18, 28 << 2, 3, 63 << 2, ord("("), ord("N"), 0, 0, 0, 0))
    assert mitbih.parse_atr(aux) == [mitbih.Annotation(18, 28, "(N")]
    # SKIP of 5000 samples, then a normal beat with delta 0.
    skip = bytes((0, 59 << 2, 0, 0, 5000 & 0xFF, (5000 >> 8) & 0xFF, 0, 1 << 2, 0, 0))
    assert mitbih.parse_atr(skip) == [mitbih.Annotation(5000, 1, "")]
    with pytest.raises(RuntimeError, match="odd"):
        mitbih.parse_atr(b"\x00")
    # AUX claims three bytes but the file ends on that pair.
    with pytest.raises(RuntimeError, match="truncated"):
        mitbih.parse_atr(bytes((18, 1 << 2, 3, 63 << 2)))


def test_fetch_downloads_only_when_the_cache_mismatches(tmp_path, monkeypatch):
    files = {"100.hea": b"H", "100.dat": b"DD", "100.atr": b"A"}
    meta = {
        "base_url": "https://physionet.example/files/mitdb/1.0.0/",
        "files": [
            {"name": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
            for name, body in files.items()
        ],
    }
    monkeypatch.setattr(mitbih, "load_manifest", lambda: meta)
    calls = []

    def fake_download(url, dest):
        calls.append(url)
        dest.write_bytes(files[url.rsplit("/", 1)[-1]])

    monkeypatch.setattr(mitbih, "_download", fake_download)
    first = mitbih.fetch(tmp_path)
    assert calls == [meta["base_url"] + name for name in files]
    calls.clear()
    assert mitbih.fetch(first) == first
    assert calls == []
    (tmp_path / "100.dat").write_bytes(b"nope")
    assert mitbih.fetch(tmp_path) == tmp_path
    assert calls == [meta["base_url"] + "100.dat"]
    assert (tmp_path / "100.dat").read_bytes() == b"DD"


def test_fetch_reports_a_failed_download(tmp_path, monkeypatch):
    meta = mitbih.load_manifest()
    monkeypatch.setattr(mitbih, "load_manifest", lambda: meta)

    def boom(url, dest):
        raise OSError("offline")

    monkeypatch.setattr(mitbih, "_download", boom)
    with pytest.raises(RuntimeError, match="could not download 100.hea"):
        mitbih.fetch(tmp_path)


def test_matlab_load_of_a_synthetic_record(tmp_path):
    samples = np.array([[995, 1011], [1024, 824]], dtype=np.int32)
    directory = _write_record(tmp_path / "rec", samples)
    # Sample 0 in the file is MATLAB index 1.
    (directory / "rec.atr").write_bytes(bytes((0, 1 << 2, 0, 0)))
    session = Session.create_default()
    repl = ReplSession(session)
    repl.run_line(
        f"R = mitbih_load('{directory.as_posix()}'); fs = R.fs; n = size(R.sig, 1); "
        "c = size(R.sig, 2); s = R.sig(1, :); res = R.resolution; ann = R.ann_sample; code = R.ann_code;"
    )
    assert _num(session, "fs") == [360.0]
    assert _num(session, "n") == [2.0]
    assert _num(session, "c") == [2.0]
    assert _num(session, "s") == pytest.approx([-0.145, -0.065])
    assert _num(session, "res") == [11.0, 11.0]
    assert _num(session, "ann") == [1.0]
    assert _num(session, "code") == [1.0]
    assert session.workspace.get("R").get("names").get(0, 0).text == "MLII"
    assert session.workspace.get("R").get("names").get(0, 1).text == "V5"


def test_matlab_wrappers_reject_extra_arguments_before_download():
    session = Session.create_default()
    repl = ReplSession(session)
    with pytest.raises(EvalError, match="Too many input arguments"):
        repl.run_line("mitbih_fetch('x');")
    with pytest.raises(EvalError, match="does not exist"):
        repl.run_line("mitbih_load('/no/such/mitbih-record');")
