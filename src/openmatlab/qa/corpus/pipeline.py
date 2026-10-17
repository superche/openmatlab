"""Corpus run pipeline: preprocess -> sandboxed run -> classify (M12 C03/C04, Epics #763/#764).

``run_corpus()`` runs every manifest entry from the local cache and returns one record per
entry (no corpus code is stored: id, tiers, category, key, a truncated message):

* ``t0`` (parse) for every entry; ``t1`` (run) for runnable script roles and driver entries.
* Rosetta script blocks are preprocessed (:mod:`.preprocess`); function blocks from the same
  page are staged next to them under their function names, so a page's helpers resolve.
* Entries with a ``call`` (chebfun self-tests, matlab2tikz ACID scenes) run that driver.
* Octave ``%!`` test files are parse-only here; their oracles are C-E5 (#765).
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

from . import manifest as M
from .classify import classify_features, features
from .preprocess import prepare
from .runner import DEFAULT_TIMEOUT, run_one

MSG_CAP = 240


def _fn_name(code: str) -> str:
    m = re.search(r"^\s*function\s+(?:\[[^\]]*\]\s*=\s*|\w+\s*=\s*)?([A-Za-z_]\w*)", code, re.M)
    return m.group(1) if m else ""


def _page(e: M.Entry) -> str:
    return e.id.rsplit("/", 1)[0]


class _Job:
    def __init__(self, e: M.Entry, cache: Path, siblings: Dict[str, str]):
        self.e, self.cache, self.siblings = e, cache, siblings

    def run(self, timeout: float) -> dict:
        e, rec = self.e, {"id": self.e.id, "source": self.e.source, "kind": self.e.kind}
        src = self.cache / e.file
        if not src.is_file():
            rec.update(t0="missing", t1="missing", category="io-env", key="cache-missing", message="not in cache")
            return rec
        raw = src.read_text(encoding="utf-8", errors="replace")
        if e.kind == "octave-tests":  # Octave %! blocks are T2/T3 material (C-E5 #765), not MATLAB files
            rec.update(role="octave-tests", notes=[], t0="n/a", t1="n/a", status="n/a", category="deferred", key="C-E5",
                       message="")
            return rec
        stage = Path(tempfile.mkdtemp(prefix="omstage-"))
        try:
            if e.call:
                code, role, notes, inputs = raw, "driver", [], None
                drv = stage / ("drv_" + re.sub(r"\W", "_", e.id)[-50:] + ".m")
                here = str(src.parent).replace("'", "''")
                drv.write_text(f"addpath('{here}');\n" + e.call.replace("{root}", self._root()) + "\n", encoding="utf-8")
                target = drv
            else:
                p = prepare(raw, self.siblings) if e.source == "rosetta" else None
                code = p.code if p else raw
                role = (p.role if p else ("script" if e.kind == "script" else "function"))
                if e.kind == "octave-tests":
                    role = "function"
                notes, inputs = (p.notes if p else []), (p.input_lines if p else None)
                target = stage / src.name
                target.write_text(code, encoding="utf-8")
                for fname, body in self.siblings.items():
                    if fname and not (stage / f"{fname}.m").exists() and fname != _fn_name(code):
                        (stage / f"{fname}.m").write_text(body, encoding="utf-8")
            rec.update(role=role, notes=notes)
            if role == "noise":  # set aside by preprocessing (dialect, fragment): not run, not in pass rates
                rec.update(t0="n/a", t1="n/a", status="n/a", category="corpus-noise", key=notes[-1].split(":")[0],
                           message=notes[-1][:MSG_CAP])
                return rec
            if role in ("script", "driver"):
                r = run_one(target, timeout=timeout, name=e.id, input_lines=inputs).to_json()
                rec["t1"] = r["status"]
                rec["t0"] = "error" if r["kind"] == "parse" and role == "script" else ("pass" if role == "script"
                                                                                       else self._parse(src, timeout))
            else:
                r = run_one(target, timeout=timeout, name=e.id, mode="parse").to_json()
                rec["t0"], rec["t1"] = r["status"], "n/a"
            feats = features(code, self.siblings, self._resolvable(r["message"]) if e.call else None)
            cat, key = classify_features(r, feats)
            rec.update(category=cat, key=key, status=r["status"], run_kind=r["kind"], features=feats, error_id=r["error_id"], message=(r["message"] or "")[:MSG_CAP],
                       elapsed=r["elapsed"])
            return rec
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def _resolvable(self, msg: str) -> dict:
        m = re.search(r"Undefined (?:function or variable|function|variable)[^:']*[:']\s*'?([A-Za-z_]\w*)", msg or "")
        if not m:
            return {}
        hits = sorted(Path(self._root()).rglob(m.group(1) + ".m"))
        if not hits:
            return {}
        parts = hits[0].parts
        where = ("private" if "private" in parts else "class-folder" if any(p.startswith("@") for p in parts)
                 else "package" if any(p.startswith("+") for p in parts) else "path")
        return {m.group(1): where}

    def _root(self) -> str:
        # cache/<source>/<sha>/... : the checkout root is the first two path components
        parts = Path(self.e.file).parts
        return str(self.cache / parts[0] / parts[1])

    def _parse(self, src: Path, timeout: float) -> str:
        return run_one(src, timeout=timeout, mode="parse").status


def jobs_for(m: M.Manifest, cache: Optional[Path] = None, ids: Optional[set] = None) -> List[_Job]:
    cache = cache or M.cache_dir()
    pages: Dict[str, Dict[str, str]] = {}
    for e in m.entries:
        if e.source == "rosetta" and e.kind == "function":
            f = cache / e.file
            if f.is_file():
                body = f.read_text(encoding="utf-8", errors="replace")
                if prepare(body).role != "function":  # a script with local functions is not a function file
                    continue
                pages.setdefault(_page(e), {})[_fn_name(body)] = body
    out = []
    for e in m.entries:
        if ids is not None and e.id not in ids:
            continue
        out.append(_Job(e, cache, pages.get(_page(e), {}) if e.source == "rosetta" else {}))
    return out


def run_corpus(m: Optional[M.Manifest] = None, *, ids: Optional[set] = None, timeout: float = DEFAULT_TIMEOUT,
               jobs: Optional[int] = None) -> List[dict]:
    m = m or M.load()
    js = jobs_for(m, ids=ids)
    with ThreadPoolExecutor(max_workers=jobs or max(1, os.cpu_count() or 2)) as ex:
        return list(ex.map(lambda j: j.run(timeout), js))
