"""BBBC038 stage1_test fetch and PNG imread (Epic #1020).

Synthetic PNGs and zips only. The Broad zip is not a fixture.
"""

from __future__ import annotations

import hashlib
import io
import struct
import subprocess
import zipfile
import zlib

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs import bbbc038
from openmatlab.libs.imread import decode_png
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()
_SIG = b"\x89PNG\r\n\x1a\n"


def _chunk(tag: bytes, body: bytes) -> bytes:
    crc = zlib.crc32(tag + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", crc)


def _png(width, height, depth, color, scanlines: bytes) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, depth, color, 0, 0, 0)
    return _SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(scanlines)) + _chunk(b"IEND", b"")


def gray_png(rows, depth=8) -> bytes:
    height, width = len(rows), len(rows[0])
    raw = bytearray()
    for row in rows:
        raw.append(0)
        if depth == 16:
            for value in row:
                raw.extend(struct.pack(">H", value))
        else:
            raw.extend(row)
    return _png(width, height, depth, 0, bytes(raw))


def _num(session, name):
    return np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def test_manifest_pins_the_broad_zip_and_one_fov():
    meta = bbbc038.load_manifest()
    assert meta["url"] == "https://data.broadinstitute.org/bbbc/BBBC038/stage1_test.zip"
    assert meta["bytes"] == 9545388
    assert meta["license"] == "CC0-1.0"
    assert meta["doi"] == "10.1038/s41592-019-0612-7"
    assert meta["dataset"] == "BBBC038v1"
    assert len(meta["sha256"]) == 64
    assert any("Caicedo" in line for line in meta["citations"])
    fov = meta["fov"]
    assert bbbc038.member_ok(fov["member"])
    assert fov["member"].endswith(".png")
    assert fov["height"] == 256 and fov["width"] == 256
    assert fov["bit_depth"] == 8 and fov["color_type"] == 6
    assert fov["bytes"] == 29407
    assert len(fov["sha256"]) == 64


def test_cache_path_is_gitignored():
    for rel in (
        "downloads/bbbc038/stage1_test.zip",
        "downloads/bbbc038/fov/0114f484a16c152baa2d82fdd43740880a762c93f436c8988ac461c5c9dbe7d5.png",
    ):
        ignored = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT)
        assert ignored.returncode == 0, rel
    tracked = subprocess.run(["git", "ls-files", "downloads/bbbc038"], cwd=ROOT, capture_output=True, text=True)
    assert tracked.stdout.strip() == ""


def test_verify_cached_rejects_a_different_file(tmp_path):
    path = tmp_path / "stage1_test.zip"
    path.write_bytes(b"not the zip")
    spec = {"name": "stage1_test.zip", "bytes": 9545388, "sha256": "ab" * 32}
    with pytest.raises(RuntimeError, match="size"):
        bbbc038.verify_cached(path, spec)
    path.write_bytes(b"x" * 9545388)
    with pytest.raises(RuntimeError, match="sha256"):
        bbbc038.verify_cached(path, spec)


def test_content_length_must_match_when_the_header_is_present():
    bbbc038.check_content_length(None, 9545388)
    bbbc038.check_content_length("9545388", 9545388)
    with pytest.raises(RuntimeError, match="Content-Length 9 "):
        bbbc038.check_content_length("9", 9545388)
    with pytest.raises(RuntimeError, match="not an integer"):
        bbbc038.check_content_length("nope", 9545388)


def test_member_ok_rejects_parent_and_absolute_names():
    assert bbbc038.member_ok("abc/images/abc.png")
    assert not bbbc038.member_ok("../evil.png")
    assert not bbbc038.member_ok("abc/../../evil.png")
    assert not bbbc038.member_ok("/tmp/evil.png")
    assert not bbbc038.member_ok("abc\\evil.png")
    assert not bbbc038.member_ok("")


def test_grayscale_rgb_and_16bit_roundtrip():
    image, alpha = decode_png(gray_png([[10, 20], [30, 40]]))
    assert alpha is None
    assert image.dtype == np.uint8
    assert image.tolist() == [[10, 20], [30, 40]]
    image, alpha = decode_png(gray_png([[0x0102]], depth=16))
    assert image.dtype == np.uint16 and int(image[0, 0]) == 0x0102
    raw = bytes([0, 9, 8, 7])
    image, alpha = decode_png(_png(1, 1, 8, 2, raw))
    assert alpha is None
    assert image.tolist() == [[[9, 8, 7]]]
    raw = bytes([0, 10, 1, 20, 2])
    image, alpha = decode_png(_png(2, 1, 8, 4, raw))
    assert image.tolist() == [[10, 20]]
    assert alpha.tolist() == [[1, 2]]


def test_filters_sub_up_average_and_paeth():
    # Row 0 is None: 10, 20. Row 1 is Paeth, hand-computed for pixels 30, 40.
    # Predictor at (1, 0) is Up=10, so the stored byte is 20.
    # Predictor at (1, 1) is Left=30, so the stored byte is 10.
    scan = bytes([0, 10, 20, 4, 20, 10])
    image, _alpha = decode_png(_png(2, 2, 8, 0, scan))
    assert image.tolist() == [[10, 20], [30, 40]]
    # Sub on one row: pixels 10, 30, 40 store as 10, 20, 10.
    image, _alpha = decode_png(_png(3, 1, 8, 0, bytes([1, 10, 20, 10])))
    assert image.tolist() == [[10, 30, 40]]
    # Up: second row stores the difference from 5, 6.
    image, _alpha = decode_png(_png(2, 2, 8, 0, bytes([0, 5, 6, 2, 1, 2])))
    assert image.tolist() == [[5, 6], [6, 8]]
    # Average: second pixel of row 0 uses floor(left/2). Pixel 8 stores 8-floor(4/2)=6.
    image, _alpha = decode_png(_png(2, 1, 8, 0, bytes([3, 4, 6])))
    assert image.tolist() == [[4, 8]]


def test_reader_rejects_bad_pngs():
    with pytest.raises(RuntimeError, match="not a PNG"):
        decode_png(b"not a png")
    png = bytearray(gray_png([[1]]))
    # First IDAT payload byte sits after the signature, the IHDR chunk, and the IDAT header.
    png[8 + (4 + 4 + 13 + 4) + 8] ^= 0xFF
    with pytest.raises(RuntimeError, match="CRC"):
        decode_png(bytes(png))
    with pytest.raises(RuntimeError, match="interlaced"):
        decode_png(_png_interlaced())
    with pytest.raises(RuntimeError, match="color type 3"):
        decode_png(_png(1, 1, 8, 3, bytes([0, 0])))
    with pytest.raises(RuntimeError, match="bit depth 4"):
        decode_png(_png(1, 1, 4, 0, bytes([0, 0])))
    with pytest.raises(RuntimeError, match="outside"):
        decode_png(_png(4097, 1, 8, 0, bytes([0, 0])))


def _png_interlaced() -> bytes:
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 1)
    scan = zlib.compress(bytes([0, 1]))
    return _SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", scan) + _chunk(b"IEND", b"")


def test_extract_rejects_a_parent_segment(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.png", b"png")
    zpath = tmp_path / "stage1_test.zip"
    zpath.write_bytes(buf.getvalue())
    dest = tmp_path / "fov" / "evil.png"
    with pytest.raises(RuntimeError, match="safe zip path"):
        bbbc038.extract_fov(zpath, dest, {"member": "../evil.png", "bytes": 3, "sha256": "ab" * 32})
    assert not dest.exists()
    assert not (tmp_path.parent / "evil.png").exists()


def test_fetch_downloads_only_when_the_cache_mismatches(tmp_path, monkeypatch):
    png = gray_png([[1, 2], [3, 4]])
    member = "abc/images/abc.png"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member, png)
        zf.writestr("../evil.png", b"nope")
    blob = buf.getvalue()
    meta = {
        "url": "https://broad.example/bbbc/BBBC038/stage1_test.zip",
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "fov": {"member": member, "bytes": len(png), "sha256": hashlib.sha256(png).hexdigest()},
    }
    monkeypatch.setattr(bbbc038, "load_manifest", lambda: meta)
    calls = []

    def fake_download(url, dest, expected):
        calls.append((url, expected))
        dest.write_bytes(blob)

    monkeypatch.setattr(bbbc038, "_download", fake_download)
    cache = bbbc038.fetch(tmp_path)
    assert calls == [(meta["url"], len(blob))]
    assert cache.image.name == "abc.png"
    assert cache.image.read_bytes() == png
    assert cache.nbytes == len(blob)
    assert not (tmp_path / "evil.png").exists()
    calls.clear()
    assert bbbc038.fetch(tmp_path).image == cache.image
    assert calls == []
    cache.image.write_bytes(b"nope")
    assert bbbc038.fetch(tmp_path).image.read_bytes() == png
    assert calls == []
    cache.zip_path.write_bytes(b"nope")
    assert bbbc038.fetch(tmp_path).nbytes == len(blob)
    assert calls == [(meta["url"], len(blob))]


def test_fetch_reports_a_failed_download(tmp_path, monkeypatch):
    def boom(url, dest, expected):
        raise OSError("offline")

    monkeypatch.setattr(bbbc038, "_download", boom)
    with pytest.raises(RuntimeError, match="could not download stage1_test.zip"):
        bbbc038.fetch(tmp_path)


def test_download_rejects_a_different_content_length(tmp_path, monkeypatch):
    class Resp:
        headers = {"Content-Length": "4"}

        def read(self, n=-1):
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(bbbc038.urllib.request, "urlopen", lambda *args, **kwargs: Resp())
    dest = tmp_path / "stage1_test.zip"
    with pytest.raises(RuntimeError, match="Content-Length"):
        bbbc038._download("https://broad.example/stage1_test.zip", dest, 9545388)
    assert not dest.exists()
    assert not dest.with_name(dest.name + ".partial").exists()


def test_matlab_imread_of_a_synthetic_png(tmp_path):
    path = tmp_path / "g.png"
    path.write_bytes(gray_png([[10, 20], [30, 40]]))
    session = Session.create_default()
    repl = ReplSession(session)
    repl.run_line(
        f"I = imread('{path.as_posix()}'); h = size(I, 1); w = size(I, 2); c = size(I, 3); "
        "k = double(strcmp(class(I), 'uint8')); p = double(I(1, :));"
    )
    assert _num(session, "h") == [2]
    assert _num(session, "w") == [2]
    assert _num(session, "c") == [1]
    assert _num(session, "k") == [1]
    assert _num(session, "p") == [10, 20]
    rgba = tmp_path / "c.png"
    rgba.write_bytes(_png(1, 1, 8, 6, bytes([0, 9, 8, 7, 6])))
    repl.run_line(
        f"[A, map, alpha] = imread('{rgba.as_posix()}'); p = double(A(1, 1, :)); "
        "q = double(alpha); nmap = numel(map);"
    )
    assert _num(session, "p") == [9, 8, 7]
    assert _num(session, "q") == [6]
    assert _num(session, "nmap") == [0]


def test_matlab_wrappers_reject_extra_arguments_before_download():
    session = Session.create_default()
    repl = ReplSession(session)
    with pytest.raises(EvalError, match="Too many input arguments"):
        repl.run_line("bbbc038_fetch('x');")
    with pytest.raises(EvalError, match="Too many input arguments"):
        repl.run_line("imread('a.png', 'png');")
    with pytest.raises(EvalError, match="does not exist"):
        repl.run_line("imread('/no/such/bbbc038.png');")
