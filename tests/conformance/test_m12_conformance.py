"""Real-script compatibility gate (docs/milestones/M12-corpus-gate.md) conformance suite."""

from __future__ import annotations

import importlib.util
import json

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

from ._ms_harness import SCRIPTS, params
from .m2_expected import assert_close, coerce_expected
from .m12_manifest import CRITERIA

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]


def _check(cid, got: dict, expected: dict):
    for name, want in expected.items():
        assert_close(np.asarray(got[name], dtype=float), np.asarray(coerce_expected(want), dtype=float), label=f"{cid} {name}")


def _run_m(cid, script):
    s = Session.create_default()
    r = ReplSession(s)
    queue = SCRIPTS / f"{script}.queue"
    if queue.is_file():
        r.feed_input(queue.read_text().splitlines())
    r.run_line(f'run("{(SCRIPTS / f"{script}.m").as_posix()}");')
    expected = json.loads((SCRIPTS / f"{script}.expected.json").read_text())
    _check(cid, {n: s.workspace.get(n).backend_buffer() for n in expected}, expected)


def _run_py(cid, script, tmp_path):
    spec = importlib.util.spec_from_file_location(script, SCRIPTS / f"{script}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _check(cid, mod.run(tmp_path), json.loads((SCRIPTS / f"{script}.expected.json").read_text()))


@pytest.mark.parametrize("cid,script", params(CRITERIA))
def test_m12_criterion(cid: str, script: str, tmp_path):
    if (SCRIPTS / f"{script}.py").is_file():
        _run_py(cid, script, tmp_path)
    else:
        _run_m(cid, script)


def test_m12_manifest_scripts_exist():
    for cid, (script, prio, _i, status) in CRITERIA.items():
        assert (SCRIPTS / f"{script}.m").is_file() or (SCRIPTS / f"{script}.py").is_file(), cid
        assert (SCRIPTS / f"{script}.expected.json").is_file(), cid
        assert prio in {"p0", "p1", "p2"} and status in {"met", "pending"}
