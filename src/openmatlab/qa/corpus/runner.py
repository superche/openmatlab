"""Corpus runner (M12 C02): one sandboxed subprocess per script, timeout, stdin isolation, JSON.

Each script runs in its own child interpreter (``python -m openmatlab.qa.corpus._child``) with:

* a fresh temporary working directory and ``HOME`` (the script is copied in; its source
  folder is on the path so sibling functions resolve),
* ``stdin`` = ``/dev/null`` (``input`` sees end-of-file instead of hanging),
* ``MPLBACKEND=Agg`` (no windows), no proxy variables,
* POSIX rlimits on address space and CPU time, and its own process group, which is killed on
  timeout so a runaway script cannot outlive its budget or block other scripts.

The verdict travels through a side file, so whatever the script prints cannot forge it.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

DEFAULT_TIMEOUT = 30.0
MEM_LIMIT = 4 * 1024**3
OUTPUT_CAP = 64 * 1024  # bytes of stdout/stderr kept in the result
FILE_LIMIT = 16 * 1024**2  # RLIMIT_FSIZE: a script printing forever is stopped here
STATUSES = ("pass", "error", "timeout", "crash")


@dataclass
class RunResult:
    name: str
    path: str
    status: str  # pass | error | timeout | crash
    stdout: str = ""
    stderr: str = ""
    error_id: str = ""
    message: str = ""
    kind: str = ""  # parse | eval | internal | exit | timeout | ""
    elapsed: float = 0.0
    returncode: Optional[int] = None
    extra: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)


def _limits(cpu_seconds: float):
    def apply():  # runs in the child before exec
        os.setsid()
        try:
            import resource

            resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT, MEM_LIMIT))
            cpu = int(cpu_seconds) + 5
            resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 5))
            resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_LIMIT, FILE_LIMIT))
        except Exception:
            pass

    return apply if os.name == "posix" else None


def _env(home: Path, result: Path) -> dict:
    keep = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "PYTHONPATH", "VIRTUAL_ENV", "SYSTEMROOT")}
    keep.update(HOME=str(home), TMPDIR=str(home), MPLBACKEND="Agg", OPENMATLAB_RESULT=str(result),
                PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", OPENMATLAB_SANDBOX="1")
    return keep


def _cap(text: str) -> str:
    return text if len(text) <= OUTPUT_CAP else text[:OUTPUT_CAP] + "\n... [output truncated]\n"


def run_one(path: Path | str, *, timeout: float = DEFAULT_TIMEOUT, mode: str = "run", name: Optional[str] = None) -> RunResult:
    """Run one ``.m`` file in a sandboxed child; never raises for script failures."""
    src = Path(path).resolve()
    work = Path(tempfile.mkdtemp(prefix="omcorpus-"))
    try:
        target = work / src.name
        shutil.copyfile(src, target)
        result = work / ".openmatlab-result.json"
        cmd = [sys.executable, "-m", "openmatlab.qa.corpus._child", str(target), mode, str(src.parent)]
        t0 = time.monotonic()
        fo, fe = work / ".stdout", work / ".stderr"
        with open(fo, "wb") as ho, open(fe, "wb") as he:  # files, not pipes: memory stays bounded
            proc = subprocess.Popen(cmd, cwd=work, stdin=subprocess.DEVNULL, stdout=ho, stderr=he,
                                    env=_env(work, result), preexec_fn=_limits(timeout))
            try:
                proc.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
            if os.name == "posix":  # reap the whole group (system(), runaway children)
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            if timed_out:
                proc.kill()
                proc.wait()
        elapsed = round(time.monotonic() - t0, 3)
        flooded = max(fo.stat().st_size, fe.stat().st_size) >= FILE_LIMIT
        so, se = (_cap(f.read_bytes()[: OUTPUT_CAP + 1].decode("utf-8", "replace")) for f in (fo, fe))
        r = RunResult(name=name or src.name, path=str(src), status="pass", stdout=so, stderr=se, elapsed=elapsed,
                      returncode=proc.returncode)
        if timed_out:
            r.status, r.kind, r.message = "timeout", "timeout", f"timed out after {timeout:g} s"
            return r
        if flooded:
            r.status, r.kind, r.message = "error", "output-limit", f"output exceeded {FILE_LIMIT // 1024**2} MB"
            return r
        verdict = None
        if result.is_file():
            try:
                verdict = json.loads(result.read_text(encoding="utf-8"))
            except ValueError:
                verdict = None
        if verdict is None:  # child died before reporting (signal, rlimit, interpreter crash)
            r.status, r.kind = "crash", "internal"
            r.message = f"child exited with code {proc.returncode} without a result"
        else:
            r.status = verdict.get("status", "crash")
            r.kind, r.message, r.error_id = verdict.get("kind", ""), verdict.get("message", ""), verdict.get("error_id", "")
        if "Traceback (most recent call last)" in se:
            r.status, r.kind = "crash", "internal"
        return r
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_many(paths: Iterable[Path | str], *, timeout: float = DEFAULT_TIMEOUT, jobs: Optional[int] = None,
             mode: str = "run") -> List[RunResult]:
    """Run scripts in parallel, each isolated; results keep the input order."""
    paths = list(paths)
    jobs = jobs or max(1, min(len(paths), os.cpu_count() or 2))
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(lambda p: run_one(p, timeout=timeout, mode=mode), paths))
