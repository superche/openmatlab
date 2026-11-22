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
import math
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
_SELF_SCOPE = "rusage-self-direct-process-all-threads"
_NUMPY_SCOPE = "child-process-sys-modules"
_PRE = "pre-verdict-write"
RECORD_OBS_KEYS = (
    "cpu_pre_verdict_user_s",
    "cpu_pre_verdict_system_s",
    "cpu_pre_verdict_timepoint",
    "cpu_pre_verdict_scope",
    "cpu_pre_verdict_reason",
    "numpy_child_version",
    "numpy_child_file",
    "numpy_child_reason",
    "numpy_child_timepoint",
    "numpy_child_scope",
    "cpu_terminal_user_s",
    "cpu_terminal_system_s",
    "cpu_terminal_timepoint",
    "cpu_terminal_scope",
    "cpu_terminal_reason",
    "cpu_descendants_timepoint",
    "cpu_descendants_scope",
    "cpu_descendants_reason",
    "cpu_group_timepoint",
    "cpu_group_scope",
    "cpu_group_reason",
)
_FIXED_OBS = {
    "cpu_terminal_user_s": None,
    "cpu_terminal_system_s": None,
    "cpu_terminal_timepoint": "not-sampled",
    "cpu_terminal_scope": "terminal-direct-process",
    "cpu_terminal_reason": "not-sampled-terminal",
    "cpu_descendants_timepoint": "not-sampled",
    "cpu_descendants_scope": "descendants",
    "cpu_descendants_reason": "not-sampled-descendants",
    "cpu_group_timepoint": "not-sampled",
    "cpu_group_scope": "process-group",
    "cpu_group_reason": "not-sampled-process-group",
}


def _seconds(value):
    """Finite, non-negative seconds, or None. Never raises."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, int) and value.bit_length() >= 1025:
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _cpu_absent(reason: str) -> dict:
    return {
        "cpu_pre_verdict_user_s": None,
        "cpu_pre_verdict_system_s": None,
        "cpu_pre_verdict_timepoint": "not-sampled",
        "cpu_pre_verdict_scope": "not-sampled",
        "cpu_pre_verdict_reason": reason,
    }


def _cpu_matched(user, system, reason: str) -> dict:
    return {
        "cpu_pre_verdict_user_s": user,
        "cpu_pre_verdict_system_s": system,
        "cpu_pre_verdict_timepoint": _PRE,
        "cpu_pre_verdict_scope": _SELF_SCOPE,
        "cpu_pre_verdict_reason": reason,
    }


def _numpy_absent(reason: str) -> dict:
    return {
        "numpy_child_version": None,
        "numpy_child_file": None,
        "numpy_child_reason": reason,
        "numpy_child_timepoint": "not-sampled",
        "numpy_child_scope": "not-sampled",
    }


def _numpy_matched(version, path, reason: str) -> dict:
    return {
        "numpy_child_version": version,
        "numpy_child_file": path,
        "numpy_child_reason": reason,
        "numpy_child_timepoint": _PRE,
        "numpy_child_scope": _NUMPY_SCOPE,
    }


def _cpu_from_verdict(verdict: dict) -> dict:
    keys = RECORD_OBS_KEYS[:5]
    if any(key not in verdict for key in keys):
        return _cpu_absent("key-absent")
    if verdict.get("cpu_pre_verdict_timepoint") != _PRE:
        return _cpu_absent("timepoint-invalid")
    if verdict.get("cpu_pre_verdict_scope") != _SELF_SCOPE:
        return _cpu_absent("scope-invalid")
    reason = verdict.get("cpu_pre_verdict_reason")
    if reason not in ("observed", "rusage-self-failed", "cpu-value-rejected"):
        return _cpu_absent("reason-invalid")
    if reason != "observed":
        return _cpu_matched(None, None, reason)
    user = _seconds(verdict.get("cpu_pre_verdict_user_s"))
    system = _seconds(verdict.get("cpu_pre_verdict_system_s"))
    if user is None or system is None:
        return _cpu_matched(None, None, "cpu-value-rejected")
    return _cpu_matched(user, system, "observed")


def _numpy_from_verdict(verdict: dict) -> dict:
    keys = RECORD_OBS_KEYS[5:10]
    if any(key not in verdict for key in keys):
        return _numpy_absent("key-absent")
    if verdict.get("numpy_child_timepoint") != _PRE:
        return _numpy_absent("timepoint-invalid")
    if verdict.get("numpy_child_scope") != _NUMPY_SCOPE:
        return _numpy_absent("scope-invalid")
    reason = verdict.get("numpy_child_reason")
    allowed = ("observed-child-sys-modules", "numpy-not-loaded-in-child", "numpy-inspect-failed", "value-rejected")
    if reason not in allowed:
        return _numpy_absent("reason-invalid")
    version = verdict.get("numpy_child_version")
    path = verdict.get("numpy_child_file")
    if reason == "observed-child-sys-modules":
        if isinstance(version, str) and version and isinstance(path, str) and path:
            return _numpy_matched(version, path, reason)
        return _numpy_matched(None, None, "value-rejected")
    return _numpy_matched(None, None, reason)


def _apply_observation(result: "RunResult", verdict: Optional[dict], absent: Optional[str]) -> "RunResult":
    try:
        if absent is not None or verdict is None:
            rows = _cpu_absent(absent or "no-verdict-file")
            rows.update(_numpy_absent(absent or "no-verdict-file"))
        else:
            rows = _cpu_from_verdict(verdict)
            rows.update(_numpy_from_verdict(verdict))
    except Exception:
        rows = _cpu_absent("reason-invalid")
        rows.update(_numpy_absent("reason-invalid"))
    rows.update(_FIXED_OBS)
    for key, value in rows.items():
        setattr(result, key, value)
    return result


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
    cpu_pre_verdict_user_s: Optional[float] = None
    cpu_pre_verdict_system_s: Optional[float] = None
    cpu_pre_verdict_timepoint: Optional[str] = None
    cpu_pre_verdict_scope: Optional[str] = None
    cpu_pre_verdict_reason: Optional[str] = None
    numpy_child_version: Optional[str] = None
    numpy_child_file: Optional[str] = None
    numpy_child_reason: Optional[str] = None
    numpy_child_timepoint: Optional[str] = None
    numpy_child_scope: Optional[str] = None
    cpu_terminal_user_s: Optional[float] = None
    cpu_terminal_system_s: Optional[float] = None
    cpu_terminal_timepoint: Optional[str] = None
    cpu_terminal_scope: Optional[str] = None
    cpu_terminal_reason: Optional[str] = None
    cpu_descendants_timepoint: Optional[str] = None
    cpu_descendants_scope: Optional[str] = None
    cpu_descendants_reason: Optional[str] = None
    cpu_group_timepoint: Optional[str] = None
    cpu_group_scope: Optional[str] = None
    cpu_group_reason: Optional[str] = None

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


_STILL = object()
_TERMINAL_SCOPE = "terminal-direct-process"
_TERMINAL_REAP = "direct-child-reap"
_TERMINAL_OBSERVED = "observed"
_TERMINAL_WAIT4_FAILED = "wait4-failed"
_TERMINAL_REJECTED = "cpu-value-rejected"


def _store_exit(proc, sts) -> None:
    """Same ``returncode`` encoding as ``Popen._handle_exitstatus``."""
    if os.WIFSTOPPED(sts):
        proc.returncode = -os.WSTOPSIG(sts)
    else:
        proc.returncode = os.waitstatus_to_exitcode(sts)


def _wait4_under_lock(proc, flags):
    """One ``os.wait4``. Caller holds ``proc._waitpid_lock``.

    Returns the rusage of this direct child, ``None`` when that sample is gone,
    or ``_STILL`` when the child has not exited. Does not reap on ``WNOHANG``
    while the child is running.
    """
    if proc.returncode is not None:
        return None
    try:
        pid, sts, usage = os.wait4(proc.pid, flags)
    except ChildProcessError:
        if proc.returncode is None:
            _store_exit(proc, 0)
        return None
    if pid != proc.pid:
        return _STILL
    _store_exit(proc, sts)
    return usage


def _fallback_wait(proc, timeout):
    """``Popen.wait`` so a failed ``wait4`` still stores the same returncode."""
    if proc.returncode is not None:
        return
    proc.wait(timeout=timeout)


def _fallback_waitpid_locked(proc) -> None:
    """Reap with ``waitpid`` while the caller already holds the waitpid lock."""
    if proc.returncode is not None:
        return
    try:
        pid, sts = os.waitpid(proc.pid, 0)
    except ChildProcessError:
        if proc.returncode is None:
            _store_exit(proc, 0)
        return
    if pid == proc.pid and proc.returncode is None:
        _store_exit(proc, sts)


def _reap_direct(proc, timeout):
    """``Popen.wait`` contract, reaping with ``wait4``.

    Expiry raises ``TimeoutExpired`` and does not reap. A sample is the direct
    child's rusage; ``None`` means ``wait4`` did not yield one. ``returncode``
    still follows ``Popen.wait``.
    """
    started = time.monotonic()
    try:
        if proc.returncode is not None:
            return None
        end = time.monotonic() + timeout
        delay = 0.0005  # same first step as Popen._wait
        while True:
            if proc._waitpid_lock.acquire(False):
                try:
                    sample = _wait4_under_lock(proc, os.WNOHANG)
                finally:
                    proc._waitpid_lock.release()
                if sample is not _STILL:
                    return sample
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(proc.args, timeout)
            delay = min(delay * 2, remaining, 0.05)
            time.sleep(delay)
    except subprocess.TimeoutExpired:
        raise
    except Exception:
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            if proc.returncode is None:
                raise subprocess.TimeoutExpired(proc.args, timeout)
            return None
        _fallback_wait(proc, remaining)
        return None


def _reap_direct_locked(proc):
    """Blocking ``wait4``. Caller holds ``proc._waitpid_lock``."""
    try:
        while proc.returncode is None:
            sample = _wait4_under_lock(proc, 0)
            if sample is not _STILL:
                return sample
        return None
    except Exception:
        _fallback_waitpid_locked(proc)
        return None


def _stamp_terminal(result: "RunResult", usage) -> None:
    """Write the five terminal keys from one ``wait4`` sample. Never raises."""
    user = system = None
    reason = _TERMINAL_WAIT4_FAILED
    timepoint = "not-sampled"
    if usage is not None:
        user = _seconds(getattr(usage, "ru_utime", None))
        system = _seconds(getattr(usage, "ru_stime", None))
        if user is None or system is None:
            user = system = None
            reason = _TERMINAL_REJECTED
        else:
            reason = _TERMINAL_OBSERVED
            timepoint = _TERMINAL_REAP
    for key, value in {
        "cpu_terminal_user_s": user,
        "cpu_terminal_system_s": system,
        "cpu_terminal_timepoint": timepoint,
        "cpu_terminal_scope": _TERMINAL_SCOPE,
        "cpu_terminal_reason": reason,
    }.items():
        setattr(result, key, value)


def run_one(path: Path | str, *, timeout: float = DEFAULT_TIMEOUT, mode: str = "run", name: Optional[str] = None,
            input_lines: Optional[List[str]] = None) -> RunResult:
    """Run one ``.m`` file in a sandboxed child; never raises for script failures.

    ``input_lines`` (M12 C03 fixtures) answer ``input``/``keyboard`` prompts in order.
    """
    src = Path(path).resolve()
    work = Path(tempfile.mkdtemp(prefix="omcorpus-"))
    try:
        target = work / src.name
        shutil.copyfile(src, target)
        if (src.parent / "private").is_dir():  # the driver sees its folder's private functions (#766)
            try:
                (work / "private").symlink_to(src.parent / "private", target_is_directory=True)
            except OSError:
                shutil.copytree(src.parent / "private", work / "private")
        result = work / ".openmatlab-result.json"
        env = _env(work, result)
        if input_lines:
            (work / ".openmatlab-input").write_text("\n".join(input_lines) + "\n", encoding="utf-8")
            env["OPENMATLAB_INPUT"] = str(work / ".openmatlab-input")
        cmd = [sys.executable, "-m", "openmatlab.qa.corpus._child", str(target), mode, str(src.parent)]
        t0 = time.monotonic()
        fo, fe = work / ".stdout", work / ".stderr"
        with open(fo, "wb") as ho, open(fe, "wb") as he:  # files, not pipes: memory stays bounded
            proc = subprocess.Popen(cmd, cwd=work, stdin=subprocess.DEVNULL, stdout=ho, stderr=he,
                                    env=env, preexec_fn=_limits(timeout))
            usage = None
            try:
                usage = _reap_direct(proc, timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
            # Popen.kill() polls with waitpid. Hold its lock across that poll so
            # the blocking wait4 below is the reap that keeps this child's rusage.
            reap_lock = None
            if timed_out:
                reap_lock = getattr(proc, "_waitpid_lock", None)
                if reap_lock is not None:
                    reap_lock.acquire()
            try:
                if os.name == "posix":  # reap the whole group (system(), runaway children)
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
                if timed_out:
                    proc.kill()
                    usage = _reap_direct_locked(proc)
            finally:
                if reap_lock is not None:
                    reap_lock.release()
        elapsed = round(time.monotonic() - t0, 3)
        flooded = max(fo.stat().st_size, fe.stat().st_size) >= FILE_LIMIT
        so, se = (_cap(f.read_bytes()[: OUTPUT_CAP + 1].decode("utf-8", "replace")) for f in (fo, fe))
        r = RunResult(name=name or src.name, path=str(src), status="pass", stdout=so, stderr=se, elapsed=elapsed,
                      returncode=proc.returncode)
        if timed_out or proc.returncode == -signal.SIGXCPU:  # wall-clock or CPU-time budget exceeded
            r.status, r.kind, r.message = "timeout", "timeout", (f"timed out after {timeout:g} s" if timed_out else f"CPU budget exceeded ({timeout:g} s)")
            r = _apply_observation(r, None, "timeout-return-before-verdict-read")
            _stamp_terminal(r, usage)
            return r
        if flooded:
            r.status, r.kind, r.message = "error", "output-limit", f"output exceeded {FILE_LIMIT // 1024**2} MB"
            return _apply_observation(r, None, "no-verdict-file")
        verdict = None
        if result.is_file():
            try:
                verdict = json.loads(result.read_text(encoding="utf-8"))
            except ValueError:
                verdict = None
        if verdict is None:  # child died before reporting (signal, rlimit, interpreter crash)
            r.status, r.kind = "crash", "internal"
            r.message = f"child exited with code {proc.returncode} without a result"
            absent = "verdict-unparsable" if result.is_file() else "no-verdict-file"
        else:
            r.status = verdict.get("status", "crash")
            r.kind, r.message, r.error_id = verdict.get("kind", ""), verdict.get("message", ""), verdict.get("error_id", "")
            absent = None
        if "Traceback (most recent call last)" in se:
            r.status, r.kind = "crash", "internal"
        return _apply_observation(r, verdict, absent)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_many(paths: Iterable[Path | str], *, timeout: float = DEFAULT_TIMEOUT, jobs: Optional[int] = None,
             mode: str = "run") -> List[RunResult]:
    """Run scripts in parallel, each isolated; results keep the input order."""
    paths = list(paths)
    jobs = jobs or max(1, min(len(paths), os.cpu_count() or 2))
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(lambda p: run_one(p, timeout=timeout, mode=mode), paths))
