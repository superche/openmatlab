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


def test_check_cli_offline(capsys):
    from openmatlab.qa.corpus.__main__ import main

    assert main(["check"]) == 0
    assert "problems: 0" in capsys.readouterr().out
