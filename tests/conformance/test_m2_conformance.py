"""M2 Octave-breadth conformance suite (docs/milestones/M2-octave-breadth.md)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

from .m2_manifest import CRITERIA

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]

SCRIPTS = Path(__file__).resolve().parent / "scripts"


def _params():
    out = []
    for cid, (script, prio, _issues, status) in sorted(CRITERIA.items()):
        marks = []
        if status == "pending":
            marks.append(pytest.mark.xfail(strict=True, reason=f"{cid} unmet ({prio})"))
        out.append(pytest.param(cid, script, id=f"{cid}-{script}", marks=marks))
    return out


def run_script(script: str) -> dict:
    """Run scripts/<script>.m via language run(); return workspace values."""
    s = Session.create_default()
    path = SCRIPTS / f"{script}.m"
    ReplSession(s).run_line(f'run("{path}");')
    return s


@pytest.mark.parametrize("cid,script", _params())
def test_m2_criterion(cid: str, script: str):
    expected = json.loads((SCRIPTS / f"{script}.expected.json").read_text())
    s = run_script(script)
    for name, want in expected.items():
        got = np.asarray(s.workspace.get(name).backend_buffer(), dtype=float)
        want_a = np.asarray(want, dtype=float)
        if want_a.ndim == 0:
            assert got.size == 1, f"{cid} {name}: expected scalar, got {got.shape}"
            assert float(got.reshape(-1)[0]) == pytest.approx(float(want_a)), name
        else:
            assert got.shape == want_a.shape, f"{cid} {name}: {got.shape} != {want_a.shape}"
            assert np.allclose(got, want_a), f"{cid} {name}: {got} != {want_a}"


def test_manifest_scripts_exist():
    for cid, (script, prio, _i, status) in CRITERIA.items():
        assert (SCRIPTS / f"{script}.m").is_file(), cid
        assert (SCRIPTS / f"{script}.expected.json").is_file(), cid
        assert prio in {"p0", "p1", "p2"} and status in {"met", "pending"}
