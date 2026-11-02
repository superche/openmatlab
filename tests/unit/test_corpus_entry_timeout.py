"""#1059: matlab2tikz/ACID/005_markerSizes2 sits on the 20s corpus budget."""

from __future__ import annotations

import pytest

from openmatlab.qa.corpus.manifest import Entry
from openmatlab.qa.corpus.pipeline import (
    DEFAULT_CORPUS_TIMEOUT,
    ENTRY_TIMEOUT_FLOOR,
    _Job,
    timeout_for,
)

pytestmark = pytest.mark.unit

SLOW = "matlab2tikz/ACID/005_markerSizes2"


def test_floor_applies_only_at_the_default_timeout():
    assert DEFAULT_CORPUS_TIMEOUT == 20.0
    assert ENTRY_TIMEOUT_FLOOR[SLOW] == 60.0
    assert timeout_for(SLOW, DEFAULT_CORPUS_TIMEOUT) == 60.0
    assert timeout_for("matlab2tikz/ACID/004_markerSizes", DEFAULT_CORPUS_TIMEOUT) == 20.0
    assert timeout_for(SLOW, 5.0) == 5.0
    assert timeout_for(SLOW, 90.0) == 90.0


def test_cli_run_passes_the_default_timeout(tmp_path, monkeypatch):
    from openmatlab.qa.corpus.manifest import Manifest
    from openmatlab.qa.corpus.__main__ import main

    seen = {}

    def run_corpus(m, *, ids, timeout, jobs):
        seen["timeout"] = timeout
        return []

    monkeypatch.setattr("openmatlab.qa.corpus.manifest.load", lambda: Manifest({}, {}, []))
    monkeypatch.setattr("openmatlab.qa.corpus.pipeline.run_corpus", run_corpus)
    monkeypatch.setattr("openmatlab.qa.corpus.results.save", lambda *a, **k: tmp_path / "out.json")
    assert main(["run", "--out", str(tmp_path / "r.json")]) == 0
    assert seen["timeout"] == DEFAULT_CORPUS_TIMEOUT


def _entry(entry_id: str) -> Entry:
    return Entry(
        id=entry_id, source="matlab2tikz", title="", url="", revid="", sha256="",
        license="BSD-2-Clause", kind="script", file="scene.m", runnable=True,
    )


def _capture_timeout(monkeypatch):
    seen = {}

    class _R:
        def to_json(self):
            return {"status": "pass", "kind": "", "message": "", "error_id": "", "elapsed": 0.01, "stdout": "1\n"}

    def fake(path, timeout=0, **kwargs):
        seen["timeout"] = timeout
        seen["name"] = kwargs.get("name")
        return _R()

    monkeypatch.setattr("openmatlab.qa.corpus.pipeline.run_one", fake)
    return seen


def test_job_uses_the_floor_for_marker_sizes2(tmp_path, monkeypatch):
    src = tmp_path / "scene.m"
    src.write_text("disp(1)\n", encoding="utf-8")
    seen = _capture_timeout(monkeypatch)
    rec = _Job(_entry(SLOW), tmp_path, {}).run(DEFAULT_CORPUS_TIMEOUT)
    assert seen == {"timeout": 60.0, "name": SLOW}
    assert rec["status"] == "pass" and rec["t1"] == "pass"


def test_job_keeps_an_explicit_timeout_and_other_entries(tmp_path, monkeypatch):
    (tmp_path / "scene.m").write_text("disp(1)\n", encoding="utf-8")
    seen = _capture_timeout(monkeypatch)
    _Job(_entry(SLOW), tmp_path, {}).run(5.0)
    assert seen["timeout"] == 5.0
    _Job(_entry("matlab2tikz/ACID/004_markerSizes"), tmp_path, {}).run(DEFAULT_CORPUS_TIMEOUT)
    assert seen["timeout"] == 20.0
