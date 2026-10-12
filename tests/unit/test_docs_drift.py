"""Docs-vs-repo drift guard: inventories and core docs must reference real files/ids."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from openmatlab.qa.paths import repo_root

pytestmark = pytest.mark.unit

ROOT = repo_root()
CORE_DOCS = [
    "README.md",
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "docs/READY.md",
    "docs/QA.md",
    "docs/PROCESS.md",
    *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs/milestones").glob("*.md")),
    *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs/acceptance").glob("EPIC-*.md")),
]
# Concrete repo paths only: ends in a file extension or "/", not followed by a glob/template char.
REPO_PATH = re.compile(
    r"(?<![\w/.])((?:src|tests|docs|demos|scripts|features|\.github)/[\w./-]*(?:\.\w+|/))(?![\w*<{-])"
)
MD_LINK = re.compile(r"\]\(([^)#\s]+)")


def _load(name: str) -> dict:
    return yaml.safe_load((ROOT / "docs" / name).read_text(encoding="utf-8"))


def _exists(rel: str) -> bool:
    return (ROOT / rel.split("::")[0]).exists()


def test_feature_map_paths_and_cases_resolve():
    fm, cat = _load("feature_map.yaml"), _load("test_catalog.yaml")
    tc_ids = {t["id"] for t in cat["test_cases"]}
    problems = []
    for f in fm["features"]:
        for p in [*f.get("tests", []), *([f["spec"]] if f.get("spec") else [])]:
            if not _exists(p):
                problems.append(f"{f['id']}: missing path {p}")
        for c in f.get("cases", []):
            if c not in tc_ids:
                problems.append(f"{f['id']}: unknown case {c}")
    assert problems == []


def test_catalog_impl_and_narratives_resolve():
    cat = _load("test_catalog.yaml")
    problems = [
        f"{t['id']}: missing impl {t['impl']}"
        for t in cat["test_cases"]
        if t.get("impl") and not _exists(t["impl"])
    ]
    problems += [
        f"{u['id']}: missing narrative {u['narrative']}"
        for u in cat["use_cases"]
        if u.get("narrative") and not _exists(u["narrative"])
    ]
    assert problems == []


@pytest.mark.parametrize("doc", CORE_DOCS)
def test_core_doc_references_exist(doc):
    path = ROOT / doc
    text = path.read_text(encoding="utf-8")
    missing = []
    for ref in REPO_PATH.findall(text):
        ref = ref.rstrip(".,:;")
        if any(ch in ref for ch in "*<{") or "NNN" in ref:
            continue  # templates / globs, not concrete paths
        if not (ROOT / ref).exists():
            missing.append(ref)
    for link in MD_LINK.findall(text):
        if re.match(r"[a-z]+:", link):
            continue
        if not (path.parent / link).resolve().exists():
            missing.append(link)
    assert missing == []
