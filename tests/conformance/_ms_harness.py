"""Shared runner for manifest-driven milestone conformance suites (M8, M3)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

from .m2_expected import assert_close, coerce_expected

SCRIPTS = Path(__file__).resolve().parent / "scripts"
REPO = Path(__file__).resolve().parents[2]
PLUGIN_MFILES = REPO / "demos" / "plugins" / "community.signal" / "mfiles"


def params(criteria):
    out = []
    for cid, (script, prio, _issues, status) in sorted(criteria.items()):
        marks = []
        if status == "pending":
            marks.append(pytest.mark.xfail(strict=True, reason=f"{cid} unmet ({prio})"))
        out.append(pytest.param(cid, script, id=f"{cid}-{script}", marks=marks))
    return out


def run_and_check(cid: str, script: str, *, plugin: bool = False) -> None:
    expected = json.loads((SCRIPTS / f"{script}.expected.json").read_text())
    s = Session.create_default()
    r = ReplSession(s)
    if plugin:
        r.run_line(f'addpath("{PLUGIN_MFILES.as_posix()}");')
    r.run_line(f'run("{(SCRIPTS / f"{script}.m").as_posix()}");')
    for name, want in expected.items():
        got = np.asarray(s.workspace.get(name).backend_buffer(), dtype=float)
        assert_close(got, np.asarray(coerce_expected(want), dtype=float), label=f"{cid} {name}")


def check_manifest(criteria) -> None:
    for cid, (script, prio, _i, status) in criteria.items():
        assert (SCRIPTS / f"{script}.m").is_file(), cid
        assert (SCRIPTS / f"{script}.expected.json").is_file(), cid
        assert prio in {"p0", "p1", "p2"} and status in {"met", "pending"}
