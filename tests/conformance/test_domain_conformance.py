"""Domain business-conformance suite (docs/milestones/M-domain-conformance.md)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from openmatlab.extensions.host import PluginHost
from openmatlab.host.repl import ReplSession
from openmatlab.libs.path import ToolboxPath
from openmatlab.runtime.session import Session

from .domain_manifest import CRITERIA
from .m2_expected import assert_close, coerce_expected

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]

SCRIPTS = Path(__file__).resolve().parent / "scripts"
REPO = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO / "demos" / "plugins" / "community.signal"
PLUGIN_MFILES = PLUGIN_ROOT / "mfiles"

SCRIPT_CRITERIA = {k: v for k, v in CRITERIA.items() if v[0] != "plugin_which"}


def _script_params():
    out = []
    for cid, (script, prio, _issues, status) in sorted(SCRIPT_CRITERIA.items()):
        marks = []
        if status == "pending":
            marks.append(pytest.mark.xfail(strict=True, reason=f"{cid} unmet ({prio})"))
        out.append(pytest.param(cid, script, id=f"{cid}-{script}", marks=marks))
    return out


def run_domain_script(script: str):
    """Run scripts/<script>.m with community.signal mfiles on path."""
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f'addpath("{PLUGIN_MFILES.as_posix()}");')
    path = SCRIPTS / f"{script}.m"
    r.run_line(f'run("{path.as_posix()}");')
    return s


@pytest.mark.parametrize("cid,script", _script_params())
def test_domain_criterion(cid: str, script: str):
    expected = json.loads((SCRIPTS / f"{script}.expected.json").read_text())
    s = run_domain_script(script)
    for name, want in expected.items():
        got = np.asarray(s.workspace.get(name).backend_buffer(), dtype=float)
        want_a = np.asarray(coerce_expected(want), dtype=float)
        assert_close(got, want_a, label=f"{cid} {name}")


def test_domain_manifest_scripts_exist():
    for cid, (script, prio, _i, status) in CRITERIA.items():
        assert prio in {"p0", "p1", "p2"} and status in {"met", "pending"}
        if script == "plugin_which":
            continue
        assert (SCRIPTS / f"{script}.m").is_file(), cid
        assert (SCRIPTS / f"{script}.expected.json").is_file(), cid


def test_d04_plugin_which_gate():
    """D04: PluginHost discover → activate → which('hamming') without Session addpath."""
    assert CRITERIA["D04"][3] == "met"
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    warns = host.discover(
        extra=[PLUGIN_ROOT],
        include_user_dir=False,
        include_entry_points=False,
    )
    assert warns == [] or all(isinstance(w, str) for w in warns)
    host.load_all()
    host.activate_on_startup()
    hit = host.path_api.which("hamming")
    assert hit is not None, "which('hamming') must resolve via plugin pathEntries"
    assert Path(hit).name == "hamming.m"
    assert "community.signal" in Path(hit).as_posix()
