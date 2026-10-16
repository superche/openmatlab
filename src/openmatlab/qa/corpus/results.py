"""Committed corpus results (``docs/corpus/results.json``): written by ``python -m openmatlab.qa.corpus run``.

Records hold ids, tiers, categories and truncated engine messages only, never corpus code.
"""

from __future__ import annotations

import datetime as _dt
import json
import subprocess
from pathlib import Path
from typing import List, Optional

from openmatlab.qa.paths import repo_root

KEEP = ("id", "source", "kind", "role", "notes", "t0", "t1", "status", "category", "key", "error_id", "message", "elapsed")


def path() -> Path:
    return repo_root() / "docs" / "corpus" / "results.json"


def slim(records: List[dict]) -> List[dict]:
    return [{k: r[k] for k in KEEP if k in r} for r in records]


def save(records: List[dict], *, full_run: bool, timeout: float, dest: Optional[Path] = None) -> Path:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root(), capture_output=True, text=True).stdout.strip()
    except OSError:
        sha = ""
    doc = {"_doc": __doc__.strip().splitlines()[0], "full_run": full_run, "timeout": timeout, "commit": sha,
           "generated": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "records": sorted(slim(records), key=lambda r: r["id"])}
    dest = dest or path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, indent=0, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest


def load(src: Optional[Path] = None) -> dict:
    return json.loads((src or path()).read_text(encoding="utf-8"))
