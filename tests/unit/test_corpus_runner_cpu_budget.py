"""#766 / M12 C09: a child killed by its CPU rlimit (SIGXCPU) is a timeout, not an internal crash."""

from __future__ import annotations

import resource

import pytest

from openmatlab.qa.corpus import runner

pytestmark = pytest.mark.unit


def test_cpu_rlimit_is_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_limits", lambda t: (lambda: resource.setrlimit(resource.RLIMIT_CPU, (1, 3))))
    p = tmp_path / "spin.m"
    p.write_text("x = 0;\nwhile true\n  x = x + 1;\nend\n")
    r = runner.run_one(p, timeout=60)
    assert (r.status, r.kind) == ("timeout", "timeout")
    assert "CPU budget" in r.message
