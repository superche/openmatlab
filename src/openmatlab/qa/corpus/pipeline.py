"""Corpus run pipeline: preprocess -> sandboxed run -> classify (M12 C03/C04, Epics #763/#764).

``run_corpus()`` runs every manifest entry from the local cache and returns one record per
entry (no corpus code is stored: id, tiers, category, key, a truncated message):

* ``t0`` (parse) for every entry; ``t1`` (run) for runnable script roles and driver entries.
* Rosetta script blocks are preprocessed (:mod:`.preprocess`); function blocks from the same
  page are staged next to them under their function names, so a page's helpers resolve.
* Entries with a ``call`` (chebfun self-tests, matlab2tikz ACID scenes) run that driver.
* Octave ``%!`` test files: their ``%!assert``/``%!test`` blocks are the T2 tier (:mod:`.selfcheck`, C-E5 #765).
* T3 goldens (:mod:`.goldens`, C-E5 #765): Rosetta transcripts under MATLAB ``>>`` prompts, and
  Octave-produced stdout at run time only when a MATLAB doc URL is attached (Shaw 2026-10-17).
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

from . import manifest as M
from .classify import classify_features, features
from .preprocess import prepare
from . import goldens as G
from . import selfcheck
from .runner import DEFAULT_TIMEOUT, RECORD_OBS_KEYS, run_one

MSG_CAP = 240
SELF_CHECKING = ("selftest", "acid-scene")  # chebfun tests assert all(pass); matlab2tikz ACID scenes

# CLI `run --timeout` default. Real hangs still die here. One entry has a higher
# floor (below); it applies only when the caller left the timeout at this default.
DEFAULT_CORPUS_TIMEOUT = 20.0

# #1059. matlab2tikz ACID scene markerSizes2 issues 13 marker styles × 10
# single-point plot() calls (130). Each plot autoscales and redraws the figure,
# so the entry is slow, not hung: the committed full run records 7.703 s (pass),
# and GitHub-hosted runners finished it in 18.67 s (#1050) and 18.79 s (#1038)
# or killed it at this 20 s wall (20.05 s on #1051). That pass->fail flaps the
# corpus gate on unrelated PRs, because the entry sits on the 1-in-10 PR sample
# (manifest index 330). 60 s is about 3× the observed GitHub completion. An
# explicit `--timeout` still applies to every entry, including this one.
ENTRY_TIMEOUT_FLOOR = {
    "matlab2tikz/ACID/005_markerSizes2": 60.0,
}


def timeout_for(entry_id: str, timeout: float) -> float:
    """Wall-clock budget for one entry. Floors apply only at the default timeout."""
    if timeout != DEFAULT_CORPUS_TIMEOUT:
        return timeout
    return ENTRY_TIMEOUT_FLOOR.get(entry_id, timeout)


def _fn_name(code: str) -> str:
    m = re.search(r"^\s*function\s+(?:\[[^\]]*\]\s*=\s*|\w+\s*=\s*)?([A-Za-z_]\w*)", code, re.M)
    return m.group(1) if m else ""


def _page(e: M.Entry) -> str:
    return e.id.rsplit("/", 1)[0]


class _Job:
    def __init__(self, e: M.Entry, cache: Path, siblings: Dict[str, str]):
        self.e, self.cache, self.siblings = e, cache, siblings

    def run(self, timeout: float) -> dict:
        timeout = timeout_for(self.e.id, timeout)
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
            p = None
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
            for obs_key in RECORD_OBS_KEYS:
                if obs_key in r:
                    rec[obs_key] = r[obs_key]
            # T3: MATLAB-transcript golden (C03 deprompted >> output). Octave-runtime goldens are
            # attached separately when a MATLAB doc URL is configured for the entry.
            if (role == "script" and p is not None and p.transcript
                    and G.golden_source(p.notes, raw) == "matlab"
                    and not G.nondeterministic("\n".join([code, *self.siblings.values()]))):
                ok, why = (G.golden_match(r["stdout"], p.transcript) if r["status"] == "pass"
                           else (False, "T1 " + r["status"]))
                rec["t3"] = "pass" if ok else ("error" if r["status"] == "pass" else r["status"])
                rec["oracle"] = "golden:matlab" + ("" if ok else "; " + why)
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


_PROC_CAP = 65537
_QUOTA_CAP = 129
_CPU_MAX = re.compile(r"^(max|\d+)\s+(\d+)\n?$")
_QUOTA_US = re.compile(r"^(-?\d+)\n?$")
_FORMULA = "jobs or max(1, os.cpu_count() or 2)"
_ENV_NAMES = ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH", "RUNNER_NAME", "RUNNER_ENVIRONMENT")


def _read_proc(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(_PROC_CAP)


def _read_quota(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(_QUOTA_CAP)


def _unescape(field: str) -> Optional[str]:
    out = []
    index = 0
    while index < len(field):
        if field[index] != "\\":
            out.append(field[index])
            index += 1
            continue
        digits = field[index + 1:index + 4]
        if len(digits) != 3 or any(ch not in "01234567" for ch in digits):
            return None
        value = int(digits, 8)
        if value > 255:
            return None
        out.append(chr(value))
        index += 4
    return "".join(out)


def _components(path: str) -> Optional[List[str]]:
    """Absolute path components. ``/`` is an empty list. Internal empties, ``.`` and ``..`` are rejected."""
    if not isinstance(path, str) or "\x00" in path or not path.startswith("/"):
        return None
    rest = path[1:]
    if rest == "":
        return []
    parts = rest.split("/")
    if any(part == "" or part == "." or part == ".." for part in parts):
        return None
    return parts


def _map_cgroup(root: str, mount: str, cgroup_path: str) -> Optional[str]:
    """Quota directory, or None when the mapping is unreliable. No string-prefix join."""
    if cgroup_path == "":
        return None
    root_parts = _components(root)
    mount_parts = _components(mount)
    cgroup_parts = _components(cgroup_path)
    if root_parts is None or mount_parts is None or cgroup_parts is None or mount_parts == []:
        return None
    if cgroup_parts[:len(root_parts)] != root_parts:
        return None
    joined = mount_parts + cgroup_parts[len(root_parts):]
    if joined[:len(mount_parts)] != mount_parts:
        return None
    return "/" + "/".join(joined)


def _split_fields(line: str) -> Optional[List[str]]:
    fields = []
    for raw in line.split(" "):
        text = _unescape(raw)
        if text is None:
            return None
        fields.append(text)
    return fields


def _one_cgroup2(blob: bytes) -> Optional[tuple]:
    found = []
    for line in blob.decode("utf-8", "replace").splitlines():
        if not line:
            continue
        fields = _split_fields(line)
        if fields is None:
            return None
        if "-" not in fields:
            continue
        sep = fields.index("-")
        if sep + 1 >= len(fields) or fields[sep + 1] != "cgroup2":
            continue
        if sep < 5:
            return None
        found.append((fields[3], fields[4]))
    if len(found) != 1:
        return None
    return found[0]


def _one_cgroup_path(blob: bytes):
    rows = []
    for line in blob.decode("utf-8", "replace").splitlines():
        if line.startswith("0::"):
            rows.append(line[3:])
    if len(rows) != 1:
        return False
    return rows[0]


def _limit(raw, path, reason: str, kind: str) -> dict:
    return {
        "cpu_limit_raw": raw,
        "cpu_limit_path": path,
        "cpu_limit_reason": reason,
        "cpu_limit_kind": kind,
        "cpu_effective_quota": None,
        "cpu_effective_quota_reason": "effective-quota-unresolved",
    }


def _interpret_quota(data: bytes, path: str, *, v1: bool) -> dict:
    if len(data) >= _QUOTA_CAP:
        return _limit(data[:128].decode("utf-8", "replace"), path, "limit-file-unparsed", "unparsed")
    raw = data.decode("utf-8", "replace")
    if v1:
        kind = "quota-only" if _QUOTA_US.fullmatch(raw) else None
    else:
        match = _CPU_MAX.fullmatch(raw)
        if match is None:
            kind = None
        elif match.group(1) == "max":
            kind = "max-token"
        else:
            kind = "integer-pair"
    if kind is None:
        return _limit(raw, path, "limit-file-unparsed", "unparsed")
    return _limit(raw, path, "raw-limit-observed", kind)


def _read_limit_file(directory: str) -> dict:
    cpu_max = directory + "/cpu.max"
    try:
        data = _read_quota(cpu_max)
    except FileNotFoundError:
        alt = directory + "/cpu.cfs_quota_us"
        try:
            data = _read_quota(alt)
        except FileNotFoundError:
            return _limit(None, None, "limit-file-missing", "unparsed")
        except OSError:
            return _limit(None, None, "limit-file-unreadable", "unparsed")
        return _interpret_quota(data, alt, v1=True)
    except OSError:
        return _limit(None, None, "limit-file-unreadable", "unparsed")
    return _interpret_quota(data, cpu_max, v1=False)


def _cpu_limit() -> dict:
    """Raw cgroup limit at pool construction. Effective quota stays unknown."""
    unresolved = _limit(None, None, "location-unresolved", "unparsed")
    try:
        try:
            mount_blob = _read_proc("/proc/self/mountinfo")
        except OSError:
            return unresolved
        if len(mount_blob) >= _PROC_CAP:
            return unresolved
        parsed = _one_cgroup2(mount_blob)
        if parsed is None:
            return unresolved
        root, mount = parsed
        if _components(root) is None or _components(mount) in (None, []):
            return unresolved
        try:
            cgroup_blob = _read_proc("/proc/self/cgroup")
        except OSError:
            return unresolved
        if len(cgroup_blob) >= _PROC_CAP:
            return unresolved
        cgroup_path = _one_cgroup_path(cgroup_blob)
        if cgroup_path is False:
            return unresolved
        directory = _map_cgroup(root, mount, cgroup_path)
        if directory is None:
            return unresolved
        return _read_limit_file(directory)
    except Exception:
        return unresolved


def _parent_numpy() -> dict:
    try:
        mod = sys.modules.get("numpy")
        if mod is None:
            return {"numpy_version": None, "numpy_file": None, "numpy_reason": "numpy-not-loaded-in-parent"}
        version = getattr(mod, "__version__", None)
        path = getattr(mod, "__file__", None)
        if isinstance(version, str) and version and isinstance(path, str) and path:
            return {"numpy_version": version, "numpy_file": path, "numpy_reason": "observed-parent-sys-modules"}
        return {"numpy_version": None, "numpy_file": None, "numpy_reason": "numpy-inspect-failed"}
    except Exception:
        return {"numpy_version": None, "numpy_file": None, "numpy_reason": "numpy-inspect-failed"}


def _runner_env() -> list:
    rows = []
    for name in _ENV_NAMES:
        if name not in os.environ:
            rows.append({"name": name, "value": None, "reason": "env-unset"})
            continue
        value = os.environ.get(name)
        if isinstance(value, str) and value:
            rows.append({"name": name, "value": value, "reason": "observed"})
        else:
            rows.append({"name": name, "value": None, "reason": "value-rejected"})
    return rows


def build_run_observation(jobs: Optional[int], effective_workers: int, cpu_seen: List) -> dict:
    if not cpu_seen:
        cpu_count, cpu_reason = None, "not-evaluated-jobs-truthy"
    elif cpu_seen[0] is None:
        cpu_count, cpu_reason = None, "os-cpu-count-returned-none"
    elif isinstance(cpu_seen[0], int) and not isinstance(cpu_seen[0], bool):
        cpu_count, cpu_reason = cpu_seen[0], "observed"
    else:
        cpu_count, cpu_reason = None, "os-cpu-count-returned-none"
    if jobs is None:
        jobs_reason = "jobs-none"
    elif not jobs:
        jobs_reason = "jobs-falsy"
    else:
        jobs_reason = "jobs-truthy"
    doc = {
        "timepoint": "pool-construction",
        "jobs_requested": jobs,
        "jobs_requested_reason": jobs_reason,
        "cpu_count_observed": cpu_count,
        "cpu_count_reason": cpu_reason,
        "effective_workers": effective_workers,
        "effective_workers_formula": _FORMULA,
    }
    try:
        doc.update(_cpu_limit())
    except Exception:
        doc.update(_limit(None, None, "location-unresolved", "unparsed"))
    try:
        doc.update(_parent_numpy())
    except Exception:
        doc.update({"numpy_version": None, "numpy_file": None, "numpy_reason": "numpy-inspect-failed"})
    try:
        doc["runner_env"] = _runner_env()
    except Exception:
        doc["runner_env"] = [{"name": name, "value": None, "reason": "env-unset"} for name in _ENV_NAMES]
    return doc


def run_corpus(m: Optional[M.Manifest] = None, *, ids: Optional[set] = None, timeout: float = DEFAULT_TIMEOUT,
               jobs: Optional[int] = None, t2: bool = True, obs: Optional[dict] = None) -> List[dict]:
    m = m or M.load()
    js = jobs_for(m, ids=ids)

    def one(j: _Job) -> List[dict]:
        rec = j.run(timeout)
        if j.e.kind in SELF_CHECKING:  # the entry's own assertions: T2 = T1 (C-E5 #765)
            rec["t2"] = rec.get("t1", "n/a")
        if j.e.kind != "octave-tests" or not t2:
            return [rec]
        blocks = selfcheck.run_octave_file(j.e, j.cache, timeout)
        rec["t2_blocks"] = f"{sum(b['t2'] == 'pass' for b in blocks)}/{len(blocks)}"
        return [rec] + blocks

    cpu_seen: List = []

    def _cpu_count():
        count = os.cpu_count()
        cpu_seen.append(count)
        return count

    effective_workers = jobs or max(1, _cpu_count() or 2)
    if obs is not None:
        try:
            obs.update(build_run_observation(jobs, effective_workers, cpu_seen))
        except Exception:
            obs.update(_limit(None, None, "location-unresolved", "unparsed"))
            obs["effective_workers"] = effective_workers
            obs["effective_workers_formula"] = _FORMULA
    with ThreadPoolExecutor(max_workers=effective_workers) as ex:
        return [r for rs in ex.map(one, js) for r in rs]
