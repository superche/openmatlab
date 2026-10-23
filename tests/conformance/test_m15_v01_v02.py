"""M15 V01/V02: PhysioNet download of record 100 and the mV scale (Epic #1008).

The three files land in downloads/mitbih/ (gitignored). This test needs the
network only when that cache is empty or a hash does not match the manifest.
The annotation list is checked for order and range only. It is not a diagnostic golden.
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs import mitbih
from openmatlab.qa.paths import repo_root
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.conformance, pytest.mark.unit, pytest.mark.needs_numpy]

ROOT = repo_root()


def _scalar(session, name) -> float:
    return float(np.asarray(session.workspace.get(name).backend_buffer()).reshape(-1)[0])


def test_v01_v02_record100_download_and_millivolts():
    out = mitbih.fetch()
    meta = mitbih.load_manifest()
    for spec in meta["files"]:
        path = out / spec["name"]
        mitbih.verify_cached(path, spec)
        ignored = subprocess.run(["git", "check-ignore", "-q", f"downloads/mitbih/{spec['name']}"], cwd=ROOT)
        assert ignored.returncode == 0
    tracked = subprocess.run(["git", "ls-files", "downloads/mitbih"], cwd=ROOT, capture_output=True, text=True)
    assert tracked.stdout.strip() == ""

    rec = mitbih.load_record(out)
    assert rec.header.name == "100"
    assert rec.header.fs == 360
    assert rec.header.n_samples == 650000
    assert rec.sig_mv.shape == (650000, 2)
    assert rec.header.signals[0].description == "MLII"
    assert rec.header.signals[1].description == "V5"
    assert rec.header.signals[0].adc_resolution == 11
    assert rec.header.signals[0].gain == 200
    assert rec.header.signals[0].baseline == 1024
    assert rec.sig_mv[0, 0] == pytest.approx(-0.145)
    assert rec.sig_mv[0, 1] == pytest.approx(-0.065)
    assert np.isfinite(rec.sig_mv).all()
    peak = float(np.max(np.abs(rec.sig_mv)))
    assert 0.5 < peak < 20.0
    assert rec.annotations
    samples = [ann.sample for ann in rec.annotations]
    assert samples[0] >= 0
    assert samples[-1] < 650000
    assert all(samples[i] < samples[i + 1] for i in range(len(samples) - 1))

    session = Session.create_default()
    repl = ReplSession(session)
    story = ROOT / "demos" / "mitbih" / "story_record100.m"
    repl.run_line(f'run("{story.as_posix()}");')
    assert _scalar(session, "fs") == 360
    assert _scalar(session, "nch") == 2
    assert _scalar(session, "ns") == 650000
    assert _scalar(session, "s0") == pytest.approx(-0.145)
    assert session.workspace.get("R").get("names").get(0, 0).text == "MLII"
