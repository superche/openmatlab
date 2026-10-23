"""M15 B-E3 (#1010): findpeaks MinPeakHeight / MinPeakDistance.

The sine crests are a closed form: at fs = 360 and 1.2 Hz the first peak is
sample 76 (1-based) and the spacing is 300 samples. That is not a copy of
the implementation.
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture
def run():
    session = Session.create_default()
    repl = ReplSession(session)

    def go(code):
        repl.run_line(code)
        return lambda name: np.asarray(session.workspace.get(name).backend_buffer(), dtype=float)

    return go


def test_sine_crests_are_the_closed_form(run):
    g = run(
        "fs = 360; n = 1200; t = (0:n-1) ./ fs;"
        "y = sin(2 .* pi .* 1.2 .* t);"
        "[pks, locs] = findpeaks(y, 'MinPeakHeight', 0.5, 'MinPeakDistance', 200);"
        "sz = size(locs);"
    )
    # t = 75/360 is exactly pi/2 for a 1.2 Hz sine, so the crest is sample 76.
    assert g("locs").reshape(-1).tolist() == [76, 376, 676, 976]
    assert np.allclose(g("pks").reshape(-1), np.ones(4))
    assert g("sz").reshape(-1).tolist() == [1, 4]


def test_distance_keeps_the_taller_peak_and_a_plateau_uses_its_first_sample(run):
    g = run(
        "y = zeros(1, 50); y(10) = 1; y(12) = 3; y(40) = 2;"
        "[p1, l1] = findpeaks(y, 'MinPeakDistance', 5);"
        "[p2, l2] = findpeaks(y, 'MinPeakHeight', 1.5);"
        "z = [0 1 1 1 0].';"
        "[p3, l3] = findpeaks(z);"
        "sz = size(l3);"
        "yc = [0 2 0 3 0].';"
        "[pc, lc] = findpeaks(yc, 'MinPeakHeight', 0);"
        "szc = size(lc);"
    )
    assert g("l1").reshape(-1).tolist() == [12, 40]
    assert g("p1").reshape(-1).tolist() == [3, 2]
    assert g("l2").reshape(-1).tolist() == [12, 40]
    assert g("l3").reshape(-1).tolist() == [2]
    assert g("p3").reshape(-1).tolist() == [1]
    assert g("sz").reshape(-1).tolist() == [1, 1]
    assert g("lc").reshape(-1).tolist() == [2, 4]
    assert g("szc").reshape(-1).tolist() == [2, 1]


def test_sample_rate_locations_are_seconds_from_zero(run):
    g = run(
        "fs = 360; n = 600; t = (0:n-1) ./ fs; y = sin(2 .* pi .* 1.2 .* t);"
        "[pks, locs] = findpeaks(y, fs, 'MinPeakDistance', 0.5);"
    )
    # 0-based index 75 -> 75/360 seconds. The next crest is one period later.
    assert g("locs").reshape(-1) == pytest.approx([75 / 360, 375 / 360])
    assert np.allclose(g("pks").reshape(-1), np.ones(2))


def test_findpeaks_rejects_a_matrix_and_a_negative_distance(run):
    with pytest.raises(EvalError):
        run("findpeaks(ones(4, 4));")
    with pytest.raises(EvalError):
        run("findpeaks(1:10, 'MinPeakDistance', -1);")
