"""Per-entry pre-verdict CPU snapshot and run-level raw cgroup limit. Issue #1084."""

from __future__ import annotations

import inspect
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from openmatlab.qa.corpus import pipeline, results
from openmatlab.qa.corpus import selfcheck as S
from openmatlab.qa.corpus._child import _attach_observation
from openmatlab.qa.corpus.manifest import Entry, Manifest
from openmatlab.qa.corpus.runner import (
    RECORD_OBS_KEYS,
    _SELF_SCOPE,
    _cpu_from_verdict,
    _seconds,
    run_one,
)

pytestmark = pytest.mark.unit

def _mount(root: str, point: str, fstype: str = "cgroup2") -> bytes:
    return f"36 35 0:27 {root} {point} rw master:1 - {fstype} {fstype} rw\n".encode()


def _verdict(**overrides) -> dict:
    row = {
        "cpu_pre_verdict_user_s": 0.1,
        "cpu_pre_verdict_system_s": 0.0,
        "cpu_pre_verdict_timepoint": "pre-verdict-write",
        "cpu_pre_verdict_scope": _SELF_SCOPE,
        "cpu_pre_verdict_reason": "observed",
    }
    row.update(overrides)
    return row


def _drive(monkeypatch, mount: bytes, cgroup=None, quota=None):
    proc_calls = []
    quota_calls = []

    def read_proc(path):
        proc_calls.append(path)
        if path.endswith("mountinfo"):
            if isinstance(mount, Exception):
                raise mount
            return mount
        if path.endswith("cgroup"):
            if isinstance(cgroup, Exception):
                raise cgroup
            return cgroup
        raise AssertionError(path)

    def read_quota(path):
        quota_calls.append(path)
        if isinstance(quota, Exception):
            raise quota
        if callable(quota):
            return quota(path)
        return quota

    monkeypatch.setattr(pipeline, "_read_proc", read_proc)
    monkeypatch.setattr(pipeline, "_read_quota", read_quota)
    return pipeline._cpu_limit(), proc_calls, quota_calls


def _assert_unknown(doc, proc_calls, quota_calls, proc_n):
    assert doc["cpu_limit_reason"] == "location-unresolved"
    assert doc["cpu_limit_raw"] is None and doc["cpu_limit_path"] is None
    assert doc["cpu_limit_kind"] == "unparsed"
    assert doc["cpu_effective_quota"] is None
    assert doc["cpu_effective_quota_reason"] == "effective-quota-unresolved"
    assert len(proc_calls) == proc_n
    assert quota_calls == []


def test_record_obs_keys_are_the_21_whitelist():
    assert len(RECORD_OBS_KEYS) == 21
    assert RECORD_OBS_KEYS[:10] == (
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
    )
    assert "cpu_descendants_user_s" not in RECORD_OBS_KEYS
    assert RECORD_OBS_KEYS == results.KEEP[-21:]


def test_seconds_reject_bool_nan_negative_and_huge_int():
    assert _seconds(True) is None
    assert _seconds(float("nan")) is None
    assert _seconds(-1) is None
    assert _seconds("1") is None
    assert _seconds(2**1024) is None
    assert _seconds(0) == 0.0


def test_observed_requires_the_self_pair():
    bad = _cpu_from_verdict(_verdict(cpu_pre_verdict_scope="descendants"))
    assert bad["cpu_pre_verdict_reason"] == "scope-invalid"
    assert bad["cpu_pre_verdict_user_s"] is None
    assert bad["cpu_pre_verdict_timepoint"] == "not-sampled"
    assert bad["cpu_pre_verdict_scope"] == "not-sampled"
    wrong_time = _cpu_from_verdict(_verdict(cpu_pre_verdict_timepoint="not-sampled"))
    assert wrong_time["cpu_pre_verdict_reason"] == "timepoint-invalid"
    huge = _cpu_from_verdict(_verdict(cpu_pre_verdict_user_s=2**1024))
    assert huge["cpu_pre_verdict_reason"] == "cpu-value-rejected"
    assert huge["cpu_pre_verdict_timepoint"] == "pre-verdict-write"
    assert huge["cpu_pre_verdict_scope"] == _SELF_SCOPE
    assert huge["cpu_pre_verdict_user_s"] is None
    good = _cpu_from_verdict(_verdict())
    assert good["cpu_pre_verdict_reason"] == "observed"
    assert good["cpu_pre_verdict_user_s"] == 0.1


def test_child_snapshot_failure_keeps_status(monkeypatch):
    import resource

    def boom(*_args, **_kwargs):
        raise OSError("no rusage")

    monkeypatch.setattr(resource, "getrusage", boom)
    out = {"status": "error", "error_id": "a:b", "message": "m", "kind": "eval"}
    _attach_observation(out)
    assert out["status"] == "error" and out["message"] == "m"
    assert out["cpu_pre_verdict_reason"] == "rusage-self-failed"
    assert out["cpu_pre_verdict_timepoint"] == "pre-verdict-write"
    assert out["cpu_pre_verdict_scope"] == _SELF_SCOPE
    assert out["cpu_pre_verdict_user_s"] is None


def test_numpy_not_loaded_is_not_not_installed():
    import sys

    saved = sys.modules.pop("numpy", None)
    out = {"status": "pass", "error_id": "", "message": "", "kind": ""}
    try:
        _attach_observation(out)
        assert out["numpy_child_reason"] == "numpy-not-loaded-in-child"
        assert out["numpy_child_version"] is None
        parent = pipeline._parent_numpy()
        assert parent["numpy_reason"] == "numpy-not-loaded-in-parent"
    finally:
        if saved is not None:
            sys.modules["numpy"] = saved
    blob = inspect.getsource(_attach_observation) + inspect.getsource(pipeline._parent_numpy)
    assert "not-installed" not in blob
    assert "numpy-not-installed" not in blob


def test_pass_error_and_timeout_rows(tmp_path):
    (tmp_path / "a.m").write_text("disp(1)\n")
    passed = run_one(tmp_path / "a.m", timeout=20)
    assert passed.status == "pass" and passed.returncode == 0
    assert passed.cpu_pre_verdict_timepoint == "pre-verdict-write"
    assert passed.cpu_pre_verdict_scope == _SELF_SCOPE
    assert passed.cpu_pre_verdict_reason in {"observed", "rusage-self-failed"}
    assert passed.cpu_terminal_reason == "not-sampled-terminal"
    assert passed.cpu_terminal_user_s is None and passed.cpu_terminal_system_s is None
    assert passed.cpu_descendants_reason == "not-sampled-descendants"
    assert passed.cpu_group_reason == "not-sampled-process-group"
    assert passed.numpy_child_reason in {
        "observed-child-sys-modules",
        "numpy-not-loaded-in-child",
        "numpy-inspect-failed",
        "value-rejected",
    }
    (tmp_path / "e.m").write_text("error('a:b','msg');\n")
    failed = run_one(tmp_path / "e.m", timeout=20)
    assert (failed.status, failed.kind, failed.returncode) == ("error", "eval", 0)
    assert failed.cpu_pre_verdict_timepoint == "pre-verdict-write"
    assert failed.cpu_pre_verdict_scope == _SELF_SCOPE
    (tmp_path / "h.m").write_text("while true\nend\n")
    hung = run_one(tmp_path / "h.m", timeout=1)
    assert hung.status == "timeout" and hung.message == "timed out after 1 s"
    assert hung.cpu_pre_verdict_reason == "timeout-return-before-verdict-read"
    assert hung.numpy_child_reason == "timeout-return-before-verdict-read"
    assert hung.cpu_pre_verdict_user_s is None
    assert hung.cpu_terminal_reason == "not-sampled-terminal"


def test_cleanup_block_is_unchanged_and_killpg_still_runs(tmp_path, monkeypatch):
    source = inspect.getsource(run_one)
    assert "os.killpg(proc.pid, signal.SIGKILL)" in source
    kill_at = source.index("os.killpg(proc.pid, signal.SIGKILL)")
    proc_kill = source.index("proc.kill()", kill_at)
    between = source[kill_at:proc_kill]
    assert "_read_proc" not in between and "open(" not in between and "waitid" not in between
    calls = []
    real = os.killpg

    def spy(pid, sig):
        calls.append(sig)
        return real(pid, sig)

    monkeypatch.setattr("openmatlab.qa.corpus.runner.os.killpg", spy)
    (tmp_path / "a.m").write_text("disp(1)\n")
    assert run_one(tmp_path / "a.m", timeout=20).status == "pass"
    assert len(calls) == 1


def test_jobs_expression_none_zero_positive_and_negative(monkeypatch):
    calls = []

    def cpu_count():
        calls.append(1)
        return 4

    monkeypatch.setattr(pipeline.os, "cpu_count", cpu_count)
    empty = Manifest({}, {}, [])
    for jobs, evaluated in ((None, True), (0, True)):
        calls.clear()
        obs = {}
        assert pipeline.run_corpus(empty, jobs=jobs, obs=obs) == []
        assert calls == ([1] if evaluated else [])
        assert obs["effective_workers"] == 4
        assert obs["cpu_count_observed"] == 4
        assert obs["cpu_count_reason"] == "observed"
    calls.clear()
    obs = {}
    assert pipeline.run_corpus(empty, jobs=3, obs=obs) == []
    assert calls == []
    assert obs["effective_workers"] == 3
    assert obs["cpu_count_observed"] is None
    assert obs["cpu_count_reason"] == "not-evaluated-jobs-truthy"
    assert obs["jobs_requested"] == 3
    none_obs = {}
    pipeline.run_corpus(empty, jobs=None, obs=none_obs)
    assert none_obs["jobs_requested"] is None and none_obs["jobs_requested_reason"] == "jobs-none"
    zero_obs = {}
    pipeline.run_corpus(empty, jobs=0, obs=zero_obs)
    assert zero_obs["jobs_requested"] == 0 and zero_obs["jobs_requested_reason"] == "jobs-falsy"
    with pytest.raises(ValueError, match="max_workers"):
        pipeline.run_corpus(empty, jobs=-1, obs={})


def test_observation_none_skips_collection_and_empty_dict_collects(monkeypatch):
    calls = []
    real = pipeline._read_proc

    def wrapped(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(pipeline, "_read_proc", wrapped)
    monkeypatch.setattr(pipeline.os, "cpu_count", lambda: (_ for _ in ()).throw(AssertionError("cpu_count")))
    empty = Manifest({}, {}, [])
    assert pipeline.run_corpus(empty, jobs=2, obs=None) == []
    assert calls == []
    obs = {}
    assert pipeline.run_corpus(empty, jobs=2, obs=obs) == []
    assert calls
    assert obs["effective_workers"] == 2
    assert obs["cpu_effective_quota"] is None
    assert obs["cpu_effective_quota_reason"] == "effective-quota-unresolved"
    assert obs["cpu_count_observed"] is None


def test_observation_exception_does_not_change_pool(monkeypatch):
    def explode(*_args, **_kwargs):
        raise RuntimeError("fill")

    monkeypatch.setattr(pipeline, "build_run_observation", explode)
    empty = Manifest({}, {}, [])
    obs = {}
    assert pipeline.run_corpus(empty, jobs=2, obs=obs) == []
    assert obs["effective_workers"] == 2
    with pytest.raises(ValueError, match="max_workers"):
        pipeline.run_corpus(empty, jobs=-1, obs={})


def test_cgroup_line_counts_failures_and_truncation(monkeypatch):
    doc, proc, quota = _drive(monkeypatch, _mount("/", "/tmp", "tmpfs"))
    _assert_unknown(doc, proc, quota, 1)
    doc, proc, quota = _drive(monkeypatch, _mount("/", "/sys/fs/cgroup") + _mount("/a", "/b"))
    _assert_unknown(doc, proc, quota, 1)
    doc, proc, quota = _drive(monkeypatch, _mount("/", "/sys/fs/cgroup"), b"1:name:/only\n")
    _assert_unknown(doc, proc, quota, 2)
    doc, proc, quota = _drive(monkeypatch, _mount("/", "/sys/fs/cgroup"), b"0::/a\n0::/b\n")
    _assert_unknown(doc, proc, quota, 2)
    doc, proc, quota = _drive(monkeypatch, FileNotFoundError("mount"))
    _assert_unknown(doc, proc, quota, 1)
    doc, proc, quota = _drive(monkeypatch, _mount("/", "/sys/fs/cgroup"), PermissionError("cg"))
    _assert_unknown(doc, proc, quota, 2)
    doc, proc, quota = _drive(monkeypatch, b"x" * 65537)
    _assert_unknown(doc, proc, quota, 1)
    doc, proc, quota = _drive(monkeypatch, _mount("/", "/sys/fs/cgroup"), b"y" * 65537)
    _assert_unknown(doc, proc, quota, 2)


def test_cgroup_success_fallback_unreadable_and_bad_lexeme(monkeypatch):
    def body(path):
        assert path == "/sys/fs/cgroup/user.slice/session.scope/cpu.max"
        return b"max 100000\n"

    doc, proc, quota = _drive(
        monkeypatch, _mount("/", "/sys/fs/cgroup"), b"0::/user.slice/session.scope\n", body,
    )
    assert len(proc) == 2 and quota == ["/sys/fs/cgroup/user.slice/session.scope/cpu.max"]
    assert doc["cpu_limit_reason"] == "raw-limit-observed"
    assert doc["cpu_limit_kind"] == "max-token"
    assert doc["cpu_limit_raw"] == "max 100000\n"
    assert doc["cpu_effective_quota"] is None
    assert doc["cpu_effective_quota_reason"] == "effective-quota-unresolved"

    def nonroot(path):
        assert path == "/cg/session.scope/cpu.max"
        return b"100 1000\n"

    doc, _proc, quota = _drive(
        monkeypatch, _mount("/user.slice", "/cg"), b"0::/user.slice/session.scope\n", nonroot,
    )
    assert quota == ["/cg/session.scope/cpu.max"]
    assert doc["cpu_limit_kind"] == "integer-pair"

    def root_cgroup(path):
        assert path == "/sys/fs/cgroup/cpu.max"
        return b"max 100000\n"

    doc, _proc, quota = _drive(monkeypatch, _mount("/", "/sys/fs/cgroup"), b"0::/\n", root_cgroup)
    assert quota == ["/sys/fs/cgroup/cpu.max"]
    assert doc["cpu_limit_kind"] == "max-token"

    def missing(path):
        if path.endswith("/cpu.max"):
            raise FileNotFoundError(path)
        assert path.endswith("/cpu.cfs_quota_us")
        return b"100000\n"

    doc, _proc, quota = _drive(
        monkeypatch, _mount("/", "/sys/fs/cgroup"), b"0::/user.slice/session.scope\n", missing,
    )
    assert [p.rsplit("/", 1)[-1] for p in quota] == ["cpu.max", "cpu.cfs_quota_us"]
    assert doc["cpu_limit_kind"] == "quota-only"
    assert doc["cpu_limit_reason"] == "raw-limit-observed"
    assert doc["cpu_effective_quota"] is None

    doc, _proc, quota = _drive(
        monkeypatch,
        _mount("/", "/sys/fs/cgroup"),
        b"0::/user.slice/session.scope\n",
        PermissionError("cpu.max"),
    )
    assert len(quota) == 1 and quota[0].endswith("/cpu.max")
    assert doc["cpu_limit_reason"] == "limit-file-unreadable"

    doc, _proc, quota = _drive(
        monkeypatch,
        _mount("/", "/sys/fs/cgroup"),
        b"0::/user.slice/session.scope\n",
        b"not-a-quota\n",
    )
    assert len(quota) == 1
    assert doc["cpu_limit_reason"] == "limit-file-unparsed"
    assert doc["cpu_limit_raw"] == "not-a-quota\n"
    assert doc["cpu_effective_quota"] is None


def test_cgroup_unreliable_paths_do_not_open_quota_files(monkeypatch):
    cases = [
        (_mount("/", "/"), b"0::/user.slice\n", 1),
        (_mount("/", "/sys/fs/cgroup"), b"0::\n", 2),
        (_mount("/", "/sys/fs/cgroup"), b"0::/user.slice/../etc\n", 2),
        (_mount("/", "/sys/fs/cgroup"), b"0::/user.slice//session\n", 2),
        (_mount("/", "/sys/fs/cgroup"), b"0::/a/./b\n", 2),
        (_mount("/user.slice", "/cg"), b"0::/user.sliceX\n", 2),
        (b"36 35 0:27 / /sys\\12 rw - cgroup2 cgroup2 rw\n", b"0::/user.slice\n", 1),
    ]
    for mount, cgroup, proc_n in cases:
        doc, proc, quota = _drive(monkeypatch, mount, cgroup, b"max 100000\n")
        _assert_unknown(doc, proc, quota, proc_n)
    assert "startswith" not in inspect.getsource(pipeline._map_cgroup)
    blob = inspect.getsource(pipeline._read_limit_file) + inspect.getsource(pipeline._cpu_limit)
    assert "openat" not in blob and "O_NOFOLLOW" not in blob and "realpath" not in blob


def test_image_version_is_env_only(monkeypatch):
    monkeypatch.delenv("ImageVersion", raising=False)
    rows = {row["name"]: row for row in pipeline._runner_env()}
    assert rows["ImageVersion"]["reason"] == "env-unset"
    assert rows["ImageVersion"]["value"] is None
    monkeypatch.setenv("ImageVersion", "2026.11.20")
    rows = {row["name"]: row for row in pipeline._runner_env()}
    assert rows["ImageVersion"] == {"name": "ImageVersion", "value": "2026.11.20", "reason": "observed"}


def test_old_json_missing_keys_and_observation_header(tmp_path):
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"timeout": 20, "records": [{"id": "a", "status": "pass"}]}))
    loaded = results.load(old)
    assert "cpu_pre_verdict_user_s" not in loaded["records"][0]
    assert "observation" not in loaded
    from openmatlab.qa.corpus.report import regressions

    assert regressions([{"id": "a", "status": "error"}], loaded["records"]) == ["a"]
    dest = tmp_path / "none.json"
    results.save([{"id": "a", "status": "pass"}], full_run=False, timeout=20, dest=dest, observation=None)
    assert "observation" not in json.loads(dest.read_text())
    dest = tmp_path / "empty.json"
    results.save([{"id": "a", "status": "pass"}], full_run=False, timeout=20, dest=dest, observation={})
    assert json.loads(dest.read_text())["observation"] == {}
    slimmed = results.slim([{"id": "a", "status": "pass", "cpu_pre_verdict_reason": "observed", "stdout": "no"}])[0]
    assert slimmed["cpu_pre_verdict_reason"] == "observed"
    assert "stdout" not in slimmed


def test_selfcheck_blocks_do_not_gain_observation_fields(tmp_path, monkeypatch):
    (tmp_path / "t.m").write_text("%!assert (1, 1)\n")
    entry = Entry(
        id="pkg/t", source="octave", title="", url="", revid="", sha256="",
        license="GPL-3.0-or-later", kind="octave-tests", file="t.m",
    )

    def fake(path, timeout=0, name=None, **_kwargs):
        from openmatlab.qa.corpus.runner import RunResult

        return RunResult(name or "t", str(path), "pass", message="ok")

    monkeypatch.setattr(S, "run_one", fake)
    records = S.run_octave_file(entry, tmp_path, 1.0)
    assert records
    banned = set(RECORD_OBS_KEYS)
    for record in records:
        assert banned.isdisjoint(record)


def test_four_hop_whitelist_reaches_saved_record(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "a.m").write_text("disp(1)\n")
    entry = Entry(
        id="demo/a", source="local", title="", url="", revid="", sha256="",
        license="MIT", kind="script", file="a.m", runnable=True,
    )
    monkeypatch.setattr(pipeline.M, "cache_dir", lambda: cache)
    monkeypatch.setattr(pipeline.os, "cpu_count", lambda: (_ for _ in ()).throw(AssertionError("cpu")))
    import numpy as np

    version, npy_file = np.__version__, np.__file__
    saved_numpy = sys.modules.pop("numpy", None)
    obs = {}
    try:
        records = pipeline.run_corpus(Manifest({}, {}, [entry]), jobs=1, timeout=20, obs=obs)
    finally:
        if saved_numpy is not None:
            sys.modules["numpy"] = saved_numpy
    assert len(records) == 1 and records[0]["status"] == "pass"
    assert set(RECORD_OBS_KEYS) <= set(records[0])
    assert records[0]["cpu_pre_verdict_timepoint"] == "pre-verdict-write"
    assert records[0]["cpu_pre_verdict_scope"] == _SELF_SCOPE
    assert records[0]["numpy_child_reason"] == "observed-child-sys-modules"
    assert records[0]["numpy_child_version"] == version
    assert records[0]["numpy_child_file"] == npy_file
    assert records[0]["numpy_child_timepoint"] == "pre-verdict-write"
    assert records[0]["numpy_child_scope"] == "child-process-sys-modules"
    assert obs["effective_workers"] == 1
    assert obs["cpu_count_observed"] is None
    assert obs["cpu_count_reason"] == "not-evaluated-jobs-truthy"
    assert obs["cpu_effective_quota_reason"] == "effective-quota-unresolved"
    assert obs["numpy_reason"] == "numpy-not-loaded-in-parent"
    assert obs["numpy_version"] is None and obs["numpy_file"] is None
    saved = results.slim(records)[0]
    assert set(RECORD_OBS_KEYS) <= set(saved)
    assert saved["numpy_child_version"] == version
    assert saved["numpy_child_file"] == npy_file
    assert saved["numpy_child_reason"] == "observed-child-sys-modules"
    dest = tmp_path / "out.json"
    results.save(records, full_run=False, timeout=20, dest=dest, observation=obs)
    doc = json.loads(dest.read_text())
    assert set(RECORD_OBS_KEYS) <= set(doc["records"][0])
    assert doc["records"][0]["numpy_child_version"] == version
    assert doc["records"][0]["numpy_child_file"] == npy_file
    assert doc["records"][0]["numpy_child_reason"] == "observed-child-sys-modules"
    assert doc["observation"]["timepoint"] == "pool-construction"
    assert doc["observation"]["numpy_reason"] == "numpy-not-loaded-in-parent"
    assert doc["observation"]["numpy_version"] is None


def test_nonzero_cpu_with_verdict(tmp_path):
    (tmp_path / "b.m").write_text("s = 0;\nfor i = 1:300000\n s = s + 1;\nend\ndisp(s);\n")
    result = run_one(tmp_path / "b.m", timeout=20)
    assert result.status == "pass" and result.returncode == 0
    assert result.stdout.strip() == "300000"
    assert result.cpu_pre_verdict_reason == "observed"
    assert result.cpu_pre_verdict_timepoint == "pre-verdict-write"
    assert result.cpu_pre_verdict_scope == _SELF_SCOPE
    user, system = result.cpu_pre_verdict_user_s, result.cpu_pre_verdict_system_s
    if user is None or system is None or user + system <= 0:
        pytest.skip(
            "RUSAGE_SELF stayed %r/%r after a 300000-iteration loop on this host"
            % (user, system)
        )
    assert user > 0 and system >= 0
    assert result.cpu_terminal_user_s is None and result.cpu_terminal_system_s is None
    assert result.cpu_descendants_reason == "not-sampled-descendants"
    assert result.cpu_group_reason == "not-sampled-process-group"


def test_busy_timeout_keeps_null_cpu_without_a_verdict(tmp_path):
    (tmp_path / "h.m").write_text("while true\nend\n")
    result = run_one(tmp_path / "h.m", timeout=1)
    assert result.status == "timeout"
    assert result.message == "timed out after 1 s"
    assert result.returncode not in (0, None)
    assert result.cpu_pre_verdict_user_s is None and result.cpu_pre_verdict_system_s is None
    assert result.cpu_pre_verdict_reason == "timeout-return-before-verdict-read"
    assert result.cpu_pre_verdict_timepoint == "not-sampled"
    assert result.numpy_child_reason == "timeout-return-before-verdict-read"
    assert result.numpy_child_version is None and result.numpy_child_file is None
    assert result.cpu_terminal_reason == "not-sampled-terminal"
    assert result.cpu_descendants_reason == "not-sampled-descendants"
    assert result.cpu_group_reason == "not-sampled-process-group"


def test_waiting_timeout_keeps_the_absent_row(tmp_path):
    (tmp_path / "w.m").write_text("pause(30);\n")
    result = run_one(tmp_path / "w.m", timeout=1)
    assert result.status == "timeout"
    assert result.message == "timed out after 1 s"
    assert result.returncode not in (0, None)
    assert result.cpu_pre_verdict_reason == "timeout-return-before-verdict-read"
    assert result.cpu_pre_verdict_user_s is None and result.cpu_pre_verdict_system_s is None
    assert result.numpy_child_reason == "timeout-return-before-verdict-read"
    assert result.cpu_terminal_user_s is None
    assert result.cpu_group_reason == "not-sampled-process-group"


def test_corrupt_verdict_json_is_unparsable(tmp_path, monkeypatch):
    real = Path.read_text

    def wrapped(self, *args, **kwargs):
        if getattr(self, "name", "") == ".openmatlab-result.json":
            self.write_bytes(b"{")
            return "{"
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", wrapped)
    (tmp_path / "a.m").write_text("disp(1)\n")
    result = run_one(tmp_path / "a.m", timeout=20)
    assert result.status == "crash" and result.returncode == 0
    assert "without a result" in result.message
    assert result.cpu_pre_verdict_reason == "verdict-unparsable"
    assert result.cpu_pre_verdict_user_s is None and result.cpu_pre_verdict_system_s is None
    assert result.cpu_pre_verdict_timepoint == "not-sampled"
    assert result.numpy_child_reason == "verdict-unparsable"
    assert result.numpy_child_version is None
    assert result.cpu_terminal_reason == "not-sampled-terminal"


def test_sigxcpu_uses_the_absent_row(tmp_path, monkeypatch):
    import resource
    import signal

    from openmatlab.qa.corpus import runner

    real_limits = runner._limits

    def tight(cpu_seconds):
        base = real_limits(cpu_seconds)

        def apply():
            if base:
                base()
            resource.setrlimit(resource.RLIMIT_CPU, (1, 2))

        return apply

    monkeypatch.setattr(runner, "_limits", tight)
    (tmp_path / "c.m").write_text("s = 0;\nwhile true\n s = s + 1;\nend\n")
    result = run_one(tmp_path / "c.m", timeout=8)
    if "CPU budget" not in result.message:
        pytest.skip(
            "SIGXCPU was not delivered on this host: status=%s message=%r returncode=%s"
            % (result.status, result.message, result.returncode)
        )
    assert result.status == "timeout"
    assert result.returncode == -signal.SIGXCPU
    assert result.message == "CPU budget exceeded (8 s)"
    assert result.cpu_pre_verdict_reason == "timeout-return-before-verdict-read"
    assert result.cpu_pre_verdict_user_s is None and result.cpu_pre_verdict_system_s is None
    assert result.numpy_child_reason == "timeout-return-before-verdict-read"
    assert result.cpu_terminal_reason == "not-sampled-terminal"
    assert "int(cpu_seconds) + 5" in inspect.getsource(real_limits)


def test_same_group_descendant_stays_out_of_the_snapshot(tmp_path, monkeypatch):
    from openmatlab.qa.corpus import runner
    from openmatlab.qa.corpus._child import _attach_observation as attach

    pidfile = tmp_path / "descendant.pid"
    real_popen = subprocess.Popen

    def popen(cmd, **kwargs):
        pre = kwargs.get("preexec_fn")

        def wrapped():
            if pre:
                pre()
            pid = os.fork()
            if pid == 0:
                try:
                    pidfile.write_text(str(os.getpid()))
                except Exception:
                    pass
                deadline = time.time() + 2
                total = 0
                while time.time() < deadline:
                    total += 1
                os._exit(0)

        kwargs["preexec_fn"] = wrapped
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", popen)
    (tmp_path / "d.m").write_text("disp(1)\n")
    result = run_one(tmp_path / "d.m", timeout=20)
    if result.status != "pass" or not pidfile.is_file():
        pytest.skip(
            "same-group descendant was not created on this host: status=%s message=%r pidfile=%s"
            % (result.status, result.message, pidfile.is_file())
        )
    assert result.returncode == 0
    assert result.cpu_pre_verdict_timepoint == "pre-verdict-write"
    assert result.cpu_pre_verdict_scope == _SELF_SCOPE
    assert result.cpu_descendants_timepoint == "not-sampled"
    assert result.cpu_descendants_scope == "descendants"
    assert result.cpu_descendants_reason == "not-sampled-descendants"
    assert result.cpu_group_timepoint == "not-sampled"
    assert result.cpu_group_scope == "process-group"
    assert result.cpu_group_reason == "not-sampled-process-group"
    assert not hasattr(result, "cpu_descendants_user_s")
    descendant = int(pidfile.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(descendant, 0)
    blob = inspect.getsource(attach)
    assert "RUSAGE_SELF" in blob and "RUSAGE_CHILDREN" not in blob


def test_concurrent_run_one_observations_stay_isolated(tmp_path):
    from openmatlab.qa.corpus import runner

    blob = inspect.getsource(runner._cpu_from_verdict) + inspect.getsource(runner._apply_observation)
    for banned in ("RUSAGE_CHILDREN", "waitid", "killpg", "os.kill", ".poll("):
        assert banned not in blob
    (tmp_path / "a.m").write_text("disp(1)\n")
    (tmp_path / "b.m").write_text("while true\nend\n")
    with ThreadPoolExecutor(max_workers=2) as pool:
        passed = pool.submit(run_one, tmp_path / "a.m", timeout=20)
        hung = pool.submit(run_one, tmp_path / "b.m", timeout=1)
        ok, timeout = passed.result(), hung.result()
    assert ok.status == "pass" and ok.returncode == 0
    assert ok.cpu_pre_verdict_timepoint == "pre-verdict-write"
    assert ok.cpu_pre_verdict_scope == _SELF_SCOPE
    assert timeout.status == "timeout" and timeout.message == "timed out after 1 s"
    assert timeout.cpu_pre_verdict_reason == "timeout-return-before-verdict-read"
    assert timeout.cpu_pre_verdict_user_s is None
    assert ok.cpu_pre_verdict_reason != timeout.cpu_pre_verdict_reason


def _samples(fn, count=30):
    fn()
    samples = []
    for _ in range(count):
        start = time.monotonic_ns()
        fn()
        samples.append((time.monotonic_ns() - start) / 1e6)
    median = statistics.median(samples)
    print("OBS_TIMING " + json.dumps({
        "n": count, "warmup": 1, "unit": "ms", "median": median, "max": max(samples), "samples": samples,
    }))
    return median


def _full_parent_record():
    import numpy as np

    row = {key: "text" for key in results.KEEP}
    row.update(
        id="demo/full",
        source="local",
        kind="script",
        role="script",
        notes=["kept"],
        t0="pass",
        t1="pass",
        t2="pass",
        t2_blocks="1/1",
        t3="pass",
        oracle="golden:matlab",
        sha256="a" * 64,
        status="pass",
        category="ok",
        key="none",
        error_id="none:id",
        message="disp",
        elapsed=1.25,
        cpu_pre_verdict_user_s=1.5,
        cpu_pre_verdict_system_s=0.25,
        cpu_pre_verdict_timepoint="pre-verdict-write",
        cpu_pre_verdict_scope=_SELF_SCOPE,
        cpu_pre_verdict_reason="observed",
        numpy_child_version=np.__version__,
        numpy_child_file=np.__file__,
        numpy_child_reason="observed-child-sys-modules",
        numpy_child_timepoint="pre-verdict-write",
        numpy_child_scope="child-process-sys-modules",
        cpu_terminal_user_s=None,
        cpu_terminal_system_s=None,
        cpu_terminal_timepoint="not-sampled",
        cpu_terminal_scope="terminal-direct-process",
        cpu_terminal_reason="not-sampled-terminal",
        cpu_descendants_timepoint="not-sampled",
        cpu_descendants_scope="descendants",
        cpu_descendants_reason="not-sampled-descendants",
        cpu_group_timepoint="not-sampled",
        cpu_group_scope="process-group",
        cpu_group_reason="not-sampled-process-group",
    )
    return row


def _full_observation_header():
    import numpy as np

    return {
        "timepoint": "pool-construction",
        "jobs_requested": 4,
        "jobs_requested_reason": "jobs-truthy",
        "cpu_count_observed": None,
        "cpu_count_reason": "not-evaluated-jobs-truthy",
        "effective_workers": 4,
        "effective_workers_formula": "jobs or max(1, os.cpu_count() or 2)",
        "cpu_limit_raw": "max 100000\n",
        "cpu_limit_path": "/sys/fs/cgroup/user.slice/session.scope/cpu.max",
        "cpu_limit_reason": "raw-limit-observed",
        "cpu_limit_kind": "max-token",
        "cpu_effective_quota": None,
        "cpu_effective_quota_reason": "effective-quota-unresolved",
        "numpy_version": np.__version__,
        "numpy_file": np.__file__,
        "numpy_reason": "observed-parent-sys-modules",
        "runner_env": [
            {"name": name, "value": "observed-value", "reason": "observed"}
            for name in ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH", "RUNNER_NAME", "RUNNER_ENVIRONMENT")
        ],
    }


def test_overhead_budgets_keep_every_sample(capsys):
    assert _samples(lambda: _attach_observation({"status": "pass", "error_id": "", "message": "", "kind": ""})) <= 1
    assert _samples(lambda: _cpu_from_verdict(_verdict(cpu_pre_verdict_user_s=2**1024))) <= 1
    assert _samples(pipeline._parent_numpy) <= 1

    proc = subprocess.run(
        ["unshare", "--mount", "--user", "--map-root-user", sys.executable, str(Path(__file__).resolve())],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode == 77:
        pytest.skip(proc.stderr.strip() or proc.stdout.strip() or "user mount namespace is not available")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    print(proc.stdout, end="")
    timings = []
    proofs = []
    for line in proc.stdout.splitlines():
        if "OBS_TIMING " in line:
            timings.append(json.loads(line.split("OBS_TIMING ", 1)[1]))
        elif "OBS_REAL " in line:
            proofs.append(json.loads(line.split("OBS_REAL ", 1)[1]))
    assert [item["branch"] for item in proofs] == ["D", "E"]
    assert proofs[0]["opens"][-1].endswith("/cpu.max") and proofs[0]["kind"] == "max-token"
    assert proofs[0]["raw"] == "max 100000\n" and proofs[0]["reason"] == "raw-limit-observed"
    assert len(proofs[0]["opens"]) == 3
    assert proofs[1]["opens"][-2].endswith("/cpu.max") and proofs[1]["opens"][-1].endswith("/cpu.cfs_quota_us")
    assert proofs[1]["kind"] == "quota-only" and proofs[1]["raw"] == "100000\n"
    assert len(proofs[1]["opens"]) == 4
    assert len(timings) == 2
    for row in timings:
        assert row["n"] == 30 and len(row["samples"]) == 30
        assert row["median"] <= 5

    out = {"status": "pass", "error_id": "", "message": "", "kind": ""}
    _attach_observation(out)
    handle = tempfile.TemporaryFile(mode="w+")

    def dump_child():
        handle.seek(0)
        handle.truncate()
        json.dump(out, handle)
        handle.flush()

    assert _samples(dump_child) <= 5
    full = _full_parent_record()
    header = _full_observation_header()
    preview = results.slim([full])[0]
    assert set(preview) == set(results.KEEP)
    assert preview["cpu_pre_verdict_user_s"] == 1.5
    assert preview["cpu_pre_verdict_reason"] == "observed"
    assert preview["numpy_child_version"] == header["numpy_version"]
    assert preview["message"] == "disp" and preview["elapsed"] == 1.25
    assert {key for key, value in preview.items() if value is None} == {
        "cpu_terminal_user_s",
        "cpu_terminal_system_s",
    }

    def dump_parent():
        json.dumps(results.slim([full])[0])
        json.dumps(header)

    assert _samples(dump_parent) <= 2
    captured = capsys.readouterr().out
    assert captured.count("OBS_TIMING ") >= 7
    print(captured)


def _run_real_cgroup_probe() -> int:
    """Real bounded reads of temporary mountinfo, cgroup, and quota files."""
    import builtins
    import shutil

    td = Path(tempfile.mkdtemp(prefix="om-cg-"))
    real_open = builtins.open
    try:
        mount = td / "point"
        scope = mount / "user.slice" / "session.scope"
        scope.mkdir(parents=True)
        cpu_max = scope / "cpu.max"
        cpu_max.write_bytes(b"max 100000\n")
        mountinfo = td / "mountinfo"
        cgroup = td / "cgroup"
        mountinfo.write_bytes(("36 35 0:27 / %s rw - cgroup2 cgroup2 rw\n" % mount).encode())
        cgroup.write_bytes(b"0::/user.slice/session.scope\n")
        pid = str(os.getpid())
        try:
            subprocess.check_call(["mount", "--bind", str(mountinfo), "/proc/%s/mountinfo" % pid])
            subprocess.check_call(["mount", "--bind", str(cgroup), "/proc/%s/cgroup" % pid])
        except (OSError, subprocess.CalledProcessError) as exc:
            print("bind mount over /proc/%s failed: %s" % (pid, exc), file=sys.stderr)
            return 77
        calls = []

        def counting(path, *args, **kwargs):
            calls.append(os.fspath(path))
            return real_open(path, *args, **kwargs)

        builtins.open = counting
        expected = ["/proc/self/mountinfo", "/proc/self/cgroup", str(cpu_max)]
        calls.clear()
        doc = pipeline._cpu_limit()
        if calls != expected or doc["cpu_limit_reason"] != "raw-limit-observed":
            print("branch D mismatch", calls, doc, file=sys.stderr)
            return 1
        if doc["cpu_limit_kind"] != "max-token" or doc["cpu_limit_raw"] != "max 100000\n":
            print("branch D values", doc, file=sys.stderr)
            return 1
        if doc["cpu_limit_path"] != str(cpu_max) or doc["cpu_effective_quota"] is not None:
            print("branch D path", doc, file=sys.stderr)
            return 1
        print("OBS_REAL " + json.dumps({
            "branch": "D", "opens": calls, "path": doc["cpu_limit_path"],
            "raw": doc["cpu_limit_raw"], "kind": doc["cpu_limit_kind"], "reason": doc["cpu_limit_reason"],
        }))

        def time_success(kind, opens):
            def fn():
                before = len(calls)
                seen = pipeline.build_run_observation(4, 4, [])
                opened = calls[before:]
                if seen["cpu_limit_reason"] != "raw-limit-observed" or seen["cpu_limit_kind"] != kind:
                    raise AssertionError("not the success branch: %s" % seen.get("cpu_limit_reason"))
                if opened != opens or seen["cpu_effective_quota"] is not None:
                    raise AssertionError(repr(opened))

            median = _samples(fn)
            if median > 5:
                print("median %s ms over 5" % median, file=sys.stderr)
                raise SystemExit(1)

        time_success("max-token", expected)
        cpu_max.unlink()
        quota = scope / "cpu.cfs_quota_us"
        quota.write_bytes(b"100000\n")
        expected_e = ["/proc/self/mountinfo", "/proc/self/cgroup", str(cpu_max), str(quota)]
        calls.clear()
        doc = pipeline._cpu_limit()
        if calls != expected_e or doc["cpu_limit_kind"] != "quota-only" or doc["cpu_limit_raw"] != "100000\n":
            print("branch E mismatch", calls, doc, file=sys.stderr)
            return 1
        if doc["cpu_limit_reason"] != "raw-limit-observed" or doc["cpu_limit_path"] != str(quota):
            print("branch E path", doc, file=sys.stderr)
            return 1
        print("OBS_REAL " + json.dumps({
            "branch": "E", "opens": calls, "path": doc["cpu_limit_path"],
            "raw": doc["cpu_limit_raw"], "kind": doc["cpu_limit_kind"], "reason": doc["cpu_limit_reason"],
        }))
        time_success("quota-only", expected_e)
        return 0
    finally:
        builtins.open = real_open
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(_run_real_cgroup_probe())
