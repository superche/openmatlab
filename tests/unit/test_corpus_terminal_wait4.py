"""Terminal CPU of the direct child, read from the wait4 that reaps it."""

from __future__ import annotations

import inspect
import math
import os
import signal
from types import SimpleNamespace

import pytest

from openmatlab.qa.corpus import runner
from openmatlab.qa.corpus.runner import RECORD_OBS_KEYS, run_one

pytestmark = pytest.mark.unit

if not hasattr(os, "wait4"):
    pytest.skip("os.wait4 is not available", allow_module_level=True)


def _assert_absent_pre_verdict(result):
    assert result.cpu_pre_verdict_user_s is None and result.cpu_pre_verdict_system_s is None
    assert result.cpu_pre_verdict_timepoint == "not-sampled"
    assert result.cpu_pre_verdict_scope == "not-sampled"
    assert result.cpu_pre_verdict_reason == "timeout-return-before-verdict-read"
    assert result.numpy_child_version is None and result.numpy_child_file is None
    assert result.numpy_child_reason == "timeout-return-before-verdict-read"
    assert result.numpy_child_timepoint == "not-sampled"
    assert result.numpy_child_scope == "not-sampled"


def _assert_group_and_descendants_unsampled(result):
    assert result.cpu_descendants_timepoint == "not-sampled"
    assert result.cpu_descendants_scope == "descendants"
    assert result.cpu_descendants_reason == "not-sampled-descendants"
    assert result.cpu_group_timepoint == "not-sampled"
    assert result.cpu_group_scope == "process-group"
    assert result.cpu_group_reason == "not-sampled-process-group"
    assert not hasattr(result, "cpu_descendants_user_s")
    assert not hasattr(result, "cpu_group_user_s")


def _assert_wall_timeout(result):
    assert result.returncode == -signal.SIGKILL
    assert (result.status, result.kind, result.message) == ("timeout", "timeout", "timed out after 1 s")
    assert 0.9 <= result.elapsed <= 2.5
    _assert_absent_pre_verdict(result)
    _assert_group_and_descendants_unsampled(result)


def _run_with_wait4_spy(tmp_path, name, source):
    real = os.wait4
    harvested = []

    def spy(pid, options):
        got = real(pid, options)
        if got[0] == pid:
            harvested.append((options, got[2]))
        return got

    monkey = pytest.MonkeyPatch()
    monkey.setattr(runner.os, "wait4", spy)
    try:
        (tmp_path / name).write_text(source)
        result = run_one(tmp_path / name, timeout=1)
    finally:
        monkey.undo()
    return result, harvested


def test_busy_and_pause_terminal_rows_come_from_wait4(tmp_path):
    busy, busy_reaps = _run_with_wait4_spy(tmp_path, "busy.m", "while true\nend\n")
    pause, pause_reaps = _run_with_wait4_spy(tmp_path, "pause.m", "pause(30);\n")
    for result, reaps in ((busy, busy_reaps), (pause, pause_reaps)):
        _assert_wall_timeout(result)
        assert len(reaps) == 1 and reaps[0][0] == 0  # blocking wait4, the wall-clock reap
        usage = reaps[0][1]
        assert result.cpu_terminal_user_s == usage.ru_utime
        assert result.cpu_terminal_system_s == usage.ru_stime
        assert math.isfinite(result.cpu_terminal_user_s) and result.cpu_terminal_user_s >= 0
        assert math.isfinite(result.cpu_terminal_system_s) and result.cpu_terminal_system_s >= 0
        assert result.cpu_terminal_timepoint == "direct-child-reap"
        assert result.cpu_terminal_scope == "terminal-direct-process"
        assert result.cpu_terminal_reason == "observed"
    assert busy.cpu_terminal_user_s >= pause.cpu_terminal_user_s + 0.2
    assert len(RECORD_OBS_KEYS) == 21


def test_wait4_failure_keeps_status_and_unknown_terminal(tmp_path, monkeypatch):
    def boom(pid, options):
        raise OSError("wait4 unavailable")

    monkeypatch.setattr(runner.os, "wait4", boom)
    (tmp_path / "h.m").write_text("while true\nend\n")
    result = run_one(tmp_path / "h.m", timeout=1)
    _assert_wall_timeout(result)
    assert result.cpu_terminal_user_s is None and result.cpu_terminal_system_s is None
    assert result.cpu_terminal_timepoint == "not-sampled"
    assert result.cpu_terminal_scope == "terminal-direct-process"
    assert result.cpu_terminal_reason == "wait4-failed"


def test_rejected_wait4_sample_keeps_status_and_unknown_terminal(tmp_path, monkeypatch):
    real = os.wait4

    def corrupt(pid, options):
        got_pid, sts, usage = real(pid, options)
        if got_pid != pid:
            return got_pid, sts, usage
        return got_pid, sts, SimpleNamespace(ru_utime=float("nan"), ru_stime=usage.ru_stime)

    monkeypatch.setattr(runner.os, "wait4", corrupt)
    (tmp_path / "h.m").write_text("while true\nend\n")
    result = run_one(tmp_path / "h.m", timeout=1)
    _assert_wall_timeout(result)
    assert result.cpu_terminal_user_s is None and result.cpu_terminal_system_s is None
    assert result.cpu_terminal_timepoint == "not-sampled"
    assert result.cpu_terminal_scope == "terminal-direct-process"
    assert result.cpu_terminal_reason == "cpu-value-rejected"


def test_reap_helpers_do_not_use_forbidden_counters():
    blob = "\n".join(
        inspect.getsource(fn)
        for fn in (
            runner.run_one,
            runner._reap_direct,
            runner._reap_direct_locked,
            runner._wait4_under_lock,
            runner._stamp_terminal,
            runner._apply_observation,
            runner._cpu_from_verdict,
        )
    )
    assert "os.wait4(" in blob
    for banned in ("RUSAGE_CHILDREN", "RUSAGE_SELF", "cpu.stat", "waitid", "WNOWAIT", "/proc/"):
        assert banned not in blob
    source = inspect.getsource(runner.run_one)
    kill_at = source.index("os.killpg(proc.pid, signal.SIGKILL)")
    proc_kill = source.index("proc.kill()", kill_at)
    between = source[kill_at:proc_kill]
    assert "_read_proc" not in between and "open(" not in between and "waitid" not in between
