"""M3-E6 (#630): community.signal hann/kaiser/butter/freqz/filtfilt."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]
MFILES = Path(__file__).resolve().parents[2] / "demos" / "plugins" / "community.signal" / "mfiles"


@pytest.fixture
def run():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line(f"addpath('{MFILES.as_posix()}');")

    def go(code):
        r.run_line(code)
        return lambda n: s.workspace.get(n)

    return go


def _n(v):
    return np.asarray(v.backend_buffer(), dtype=float)


def test_hann_and_kaiser(run):
    g = run("a = hann(5); b = kaiser(5, 2.5); c = sum(kaiser(7, 0));")
    assert np.allclose(_n(g("a")).reshape(-1), [0, 0.5, 1, 0.5, 0])
    assert abs(_n(g("c")).reshape(-1)[0] - 7) < 1e-12
    assert abs(_n(g("b")).reshape(-1)[2] - 1) < 1e-12


def test_butter_freqz_filtfilt(run):
    g = run("[b, a] = butter(2, 0.5); [h, w] = freqz([1 1], 1, 4); y = filtfilt([0.5 0.5], 1, 1:10);")
    assert np.allclose(_n(g("b")).reshape(-1), [0.2928932188134525, 0.585786437626905, 0.2928932188134525])
    assert np.allclose(_n(g("a")).reshape(-1), [1, 0, 0.17157287525380988], atol=1e-12)
    assert np.allclose(_n(g("y")).reshape(-1), np.arange(1, 11))


def test_which_points_at_plugin(run):
    g = run("w = which('hann'); hit = ~isempty(strfind(w, 'community.signal'));")
    assert _n(g("hit")).reshape(-1)[0] == 1
