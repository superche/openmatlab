"""M2 Octave-breadth conformance suite (docs/milestones/M2-octave-breadth.md)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

from .m2_expected import assert_close, coerce_expected
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


def run_script(script: str):
    """Run scripts/<script>.m via language run(); return session."""
    s = Session.create_default()
    path = SCRIPTS / f"{script}.m"
    ReplSession(s).run_line(f'run("{path}");')
    return s


@pytest.mark.parametrize("cid,script", _params())
def test_m2_criterion(cid: str, script: str):
    expected = json.loads((SCRIPTS / f"{script}.expected.json").read_text())
    s = run_script(script)
    for name, want in expected.items():
        if name.endswith(":size"):
            # Direct shape assert (#302): works for cells, chars and arrays.
            var = name[: -len(":size")]
            got_shape = list(s.workspace.get(var).shape)
            assert got_shape == list(want), f"{cid} size({var}) = {got_shape}, want {want}"
            continue
        got = np.asarray(s.workspace.get(name).backend_buffer(), dtype=float)
        want_a = np.asarray(coerce_expected(want), dtype=float)
        assert_close(got, want_a, label=f"{cid} {name}")


def test_manifest_scripts_exist():
    for cid, (script, prio, _i, status) in CRITERIA.items():
        assert (SCRIPTS / f"{script}.m").is_file(), cid
        assert (SCRIPTS / f"{script}.expected.json").is_file(), cid
        assert prio in {"p0", "p1", "p2"} and status in {"met", "pending"}
