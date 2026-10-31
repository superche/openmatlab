"""M12 C-E2 (Epic #762): corpus manifest, licence allow-list, copyleft scan, cache verification (offline)."""

from __future__ import annotations

import copy

import pytest

from openmatlab.qa.corpus import manifest as M

pytestmark = pytest.mark.unit


def test_manifest_shape_and_sources():
    m = M.load()
    assert sum(e.runnable for e in m.entries) >= 300
    assert {e.source for e in m.entries} >= {"rosetta", "octave", "chebfun", "matlab2tikz"}
    assert all(len(e.sha256) == 64 and e.url.startswith("https://") and e.revid for e in m.entries)
    assert len({e.id for e in m.entries}) == len(m.entries)


def test_manifest_holds_no_code():
    text = (M.corpus_dir() / "manifest.json").read_text()
    assert "%!assert" not in text and "\nfunction " not in text and "disp(" not in text


def test_allowlist_rejects_unknown_licence_and_copyleft_vendoring():
    m = copy.deepcopy(M.load())
    assert M.check_allowlist(m) == []
    m.sources["octave"]["policy"] = "vendor"
    m.sources["rosetta"]["license"] = "CC-BY-NC"
    probs = M.check_allowlist(m)
    assert any("octave" in p and "run time" in p for p in probs)
    assert any("CC-BY-NC" in p for p in probs)


def test_scan_flags_tracked_copy_of_runtime_entry(tmp_path, monkeypatch):
    m = M.load()
    code = "x = 1;\n  disp( x )\n"
    e = copy.deepcopy(next(e for e in m.entries if e.source == "rosetta"))
    e.extra = {"norm_sha256": M.sha256(M._norm(code))}
    m.entries = [e]
    root = M.repo_root()
    leaked = root / "tests" / "_tmp_leak_probe.m"
    leaked.write_text("x = 1;\ndisp( x )   \n")
    try:
        monkeypatch.setattr(M, "_tracked_files", lambda: [leaked, root / "README.md"])
        assert M.scan_repo_for_copyleft_bodies(m) == ["tests/_tmp_leak_probe.m"]
    finally:
        leaked.unlink()


def test_repo_is_clean_of_corpus_bodies():
    assert M.scan_repo_for_copyleft_bodies() == []


def test_rosetta_block_extraction_and_kind():
    wiki = ("==[[header|C]]==\n<syntaxhighlight lang=c>int x;</syntaxhighlight>\n"
            "=={{header|MATLAB}}==\n<syntaxhighlight lang=matlab>disp(1)</syntaxhighlight>\ntext\n"
            "<lang MATLAB>function y = f(x)\ny = x;\nend</lang>\n=={{header|Maxima}}==\n<lang>no</lang>\n")
    blocks = M.rosetta_blocks(wiki)
    assert blocks == ["disp(1)\n", "function y = f(x)\ny = x;\nend\n"]
    assert [M._kind_of(b) for b in blocks] == ["script", "function"]
    assert M._fn_name(blocks[1]) == "f"


def test_fetch_detects_hash_mismatch(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENMATLAB_CORPUS_CACHE", str(tmp_path))
    monkeypatch.setattr(M, "_gh_tarball", lambda *a, **k: tmp_path)
    m = M.load()
    e = copy.deepcopy(next(e for e in m.entries if e.source == "octave"))
    m.entries = [e]
    (tmp_path / e.file).parent.mkdir(parents=True)
    (tmp_path / e.file).write_text("tampered\n")
    assert M.fetch(m) == {e.id: "sha256 mismatch"}


def _one(source: str):
    m = M.load()
    e = copy.deepcopy(next(x for x in m.entries if x.source == source))
    m.entries = [e]
    return m, e


def test_fetch_raises_on_rosetta_http_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENMATLAB_CORPUS_CACHE", str(tmp_path))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(M, "_gh_tarball", lambda *a, **k: None)
    m, _e = _one("rosetta")

    def boom(url, retries=4):
        raise RuntimeError("fetch failed: HTTP Error 403: Forbidden")

    monkeypatch.setattr(M, "_get", boom)
    with pytest.raises(RuntimeError, match="403"):
        M.fetch(m)


def test_fetch_raises_on_octave_http_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENMATLAB_CORPUS_CACHE", str(tmp_path))
    monkeypatch.setattr(M, "_gh_tarball", lambda *a, **k: None)
    m, _e = _one("octave")

    def boom(url, retries=4):
        raise RuntimeError("fetch failed: HTTP Error 503: Service Unavailable")

    monkeypatch.setattr(M, "_get", boom)
    with pytest.raises(RuntimeError, match="503"):
        M.fetch(m)


def test_actions_missing_rosetta_does_not_fetch_live(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENMATLAB_CORPUS_CACHE", str(tmp_path))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(M, "_gh_tarball", lambda *a, **k: None)
    m, _e = _one("rosetta")

    def boom(url, retries=4):
        raise AssertionError(url)

    monkeypatch.setattr(M, "_get", boom)
    with pytest.raises(RuntimeError, match="corpus-rosetta"):
        M.fetch(m)


def test_rosetta_seed_roundtrip_checks_sha256(tmp_path, monkeypatch):
    import io
    import tarfile

    monkeypatch.setenv("OPENMATLAB_CORPUS_CACHE", str(tmp_path))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    m, e = _one("rosetta")
    code = "disp(1)\n"
    e.sha256 = M.sha256(code)
    (tmp_path / e.file).parent.mkdir(parents=True)
    (tmp_path / e.file).write_text(code)
    dest = tmp_path / "seed.tar.gz"
    M._write_rosetta_tar(m, dest)
    (tmp_path / e.file).unlink()
    monkeypatch.setattr(M, "load", lambda path=None: m)
    monkeypatch.setattr(M, "_get", lambda url, retries=4: dest.read_bytes())
    assert M.restore_rosetta().startswith("restored ")
    assert (tmp_path / e.file).read_text() == code

    def boom(url, retries=4):
        raise AssertionError(url)

    monkeypatch.setattr(M, "_get", boom)
    assert M.restore_rosetta().startswith("rosetta cache ok")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info = tarfile.TarInfo("../evil.m")
        info.size = 2
        tf.addfile(info, io.BytesIO(b"x\n"))
    (tmp_path / e.file).unlink()
    monkeypatch.setattr(M, "_get", lambda url, retries=4: buf.getvalue())
    with pytest.raises(RuntimeError, match="refusing seed path"):
        M.restore_rosetta()
    assert not (tmp_path / "rosetta").exists()
    assert not (tmp_path.parent / "evil.m").exists()


def test_rosetta_key_cli(capsys):
    from openmatlab.qa.corpus.__main__ import main

    assert main(["rosetta-key"]) == 0
    out = capsys.readouterr().out.strip()
    assert len(out) == 64 and set(out) <= set("0123456789abcdef")


def test_check_cli_offline(capsys):
    from openmatlab.qa.corpus.__main__ import main

    assert main(["check"]) == 0
    assert "problems: 0" in capsys.readouterr().out
