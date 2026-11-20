"""Per-entry pre-verdict CPU snapshot and run-level raw cgroup limit. Issue #1084."""

from __future__ import annotations

import inspect
import json
import os
import statistics
import tempfile
import time

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
    obs = {}
    records = pipeline.run_corpus(Manifest({}, {}, [entry]), jobs=1, timeout=20, obs=obs)
    assert len(records) == 1 and records[0]["status"] == "pass"
    assert set(RECORD_OBS_KEYS) <= set(records[0])
    assert records[0]["cpu_pre_verdict_timepoint"] == "pre-verdict-write"
    assert records[0]["cpu_pre_verdict_scope"] == _SELF_SCOPE
    assert obs["effective_workers"] == 1
    assert obs["cpu_count_observed"] is None
    assert obs["cpu_count_reason"] == "not-evaluated-jobs-truthy"
    assert obs["cpu_effective_quota_reason"] == "effective-quota-unresolved"
    saved = results.slim(records)[0]
    assert set(RECORD_OBS_KEYS) <= set(saved)
    dest = tmp_path / "out.json"
    results.save(records, full_run=False, timeout=20, dest=dest, observation=obs)
    doc = json.loads(dest.read_text())
    assert set(RECORD_OBS_KEYS) <= set(doc["records"][0])
    assert doc["observation"]["timepoint"] == "pool-construction"


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


def test_overhead_budgets_keep_every_sample(monkeypatch, tmp_path, capsys):
    assert _samples(lambda: _attach_observation({"status": "pass", "error_id": "", "message": "", "kind": ""})) <= 1
    assert _samples(lambda: _cpu_from_verdict(_verdict(cpu_pre_verdict_user_s=2**1024))) <= 1
    assert _samples(pipeline._parent_numpy) <= 1

    def fast_proc(path):
        if path.endswith("mountinfo"):
            return _mount("/", "/sys/fs/cgroup")
        return b"0::/user.slice/session.scope\n"

    def success(path):
        if path.endswith("cpu.cfs_quota_us"):
            raise AssertionError("extra read")
        return b"max 100000\n"

    monkeypatch.setattr(pipeline, "_read_proc", fast_proc)
    monkeypatch.setattr(pipeline, "_read_quota", success)
    assert _samples(lambda: pipeline.build_run_observation(4, 4, [])) <= 5

    def fallback(path):
        if path.endswith("/cpu.max"):
            raise FileNotFoundError(path)
        return b"100000\n"

    monkeypatch.setattr(pipeline, "_read_quota", fallback)
    assert _samples(lambda: pipeline.build_run_observation(4, 4, [])) <= 5

    out = {"status": "pass", "error_id": "", "message": "", "kind": ""}
    _attach_observation(out)
    handle = tempfile.TemporaryFile(mode="w+")

    def dump_child():
        handle.seek(0)
        handle.truncate()
        json.dump(out, handle)
        handle.flush()

    assert _samples(dump_child) <= 5
    record = {key: records_value(key) for key in results.KEEP}
    header = pipeline.build_run_observation(4, 4, [])

    def dump_parent():
        json.dumps(record)
        json.dumps(header)

    assert _samples(dump_parent) <= 2
    captured = capsys.readouterr().out
    assert captured.count("OBS_TIMING ") >= 7
    print(captured)


def records_value(key: str):
    return "a" if key == "id" else None
