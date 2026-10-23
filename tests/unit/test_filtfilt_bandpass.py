"""M15 B-E2 (#1009): filtfilt, Butterworth bandpass, and the thin bandpass wrapper.

Coefficient pins for the 0.5–40 Hz design were cross-checked with
scipy.signal.butter during development. SciPy is not a dependency. The IIR
vector is the community.signal filtfilt result for the same b, a, and x.
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

# scipy.signal.butter(2, [0.5, 40] / 180, btype="bandpass")
BP_B = [0.0787623532949336, 0.0, -0.1575247065898672, 0.0, 0.0787623532949336]
BP_A = [1.0, -3.0547566497415675, 3.4929974094631056, -1.8177403780997303, 0.37952419683859157]
IIR = [
    4.052665710455358,
    8.026229858410716,
    12.012908935571431,
    16.006042480517863,
    20.002197265723225,
    23.9994506837902,
    27.996429443752277,
    31.99162292559049,
    35.98262787022395,
    39.964946749969386,
    43.92973900469951,
    47.8594007617794,
]


@pytest.fixture
def run():
    session = Session.create_default()
    repl = ReplSession(session)

    def go(code):
        repl.run_line(code)
        return lambda name: np.asarray(session.workspace.get(name).backend_buffer(), dtype=float)

    return go


def test_filtfilt_matches_plugin_goldens(run):
    g = run(
        "y = filtfilt([0.25 0.5 0.25], [1 -0.5], [1 2 3 4 5 6 7 8 9 10 11 12]);"
        "yr = filtfilt([0.5 0.5], 1, 1:10);"
        "yc = filtfilt([0.5 0.5], 1, 5 * ones(1, 7));"
        "M = [1 2 3 4 5 6 7 8; 9 10 11 12 13 14 15 16].';"
        "ym = filtfilt([0.5 0.5], 1, M);"
        "sz = size(y); szm = size(ym);"
    )
    assert np.allclose(g("y").reshape(-1), IIR, atol=1e-12)
    assert np.allclose(g("yr").reshape(-1), np.arange(1, 11))
    assert np.allclose(g("yc").reshape(-1), np.full(7, 5.0))
    assert g("y").shape == (1, 12)
    assert g("szm").reshape(-1).tolist() == [8, 2]
    assert np.allclose(g("ym"), np.column_stack((np.arange(1, 9), np.arange(9, 17))))


def test_butter_low_high_and_bandpass_coefficients(run):
    g = run(
        "[b, a] = butter(2, 0.5);"
        "[bh, ah] = butter(2, 0.5, 'high');"
        "[b1, a1] = butter(1, 0.5);"
        "[bp, ap] = butter(2, [0.5 40] ./ 180, 'bandpass');"
        "[bp2, ap2] = butter(2, [0.5 40] ./ 180);"
    )
    assert np.allclose(g("b").reshape(-1), [0.2928932188134525, 0.585786437626905, 0.2928932188134525])
    assert np.allclose(g("a").reshape(-1), [1, 0, 0.17157287525380988], atol=1e-12)
    assert np.allclose(g("bh").reshape(-1), [0.2928932188134525, -0.5857864376269051, 0.2928932188134525])
    assert np.allclose(g("ah").reshape(-1), [1, 0, 0.17157287525380988], atol=1e-12)
    assert np.allclose(np.concatenate((g("b1").reshape(-1), g("a1").reshape(-1))), [0.5, 0.5, 1, 0], atol=1e-12)
    assert np.allclose(g("bp").reshape(-1), BP_B, atol=1e-12)
    assert np.allclose(g("ap").reshape(-1), BP_A, atol=1e-12)
    assert np.allclose(g("bp2"), g("bp"))
    assert np.allclose(g("ap2"), g("ap"))


def _mag(b, a, hz, fs):
    w = np.pi * (hz / (fs / 2.0))
    z = np.exp(1j * w)
    return abs(np.polyval(b, z) / np.polyval(a, z))


def test_bandpass_edges_and_sine_gain(run):
    g = run(
        "fs = 360; n = 3600; t = (0:n-1) ./ fs;"
        "x = sin(2 .* pi .* 10 .* t);"
        "[b, a] = butter(2, [0.5 40] ./ (fs/2), 'bandpass');"
        "y = filtfilt(b, a, x);"
        "z = bandpass(x, [0.5 40], fs);"
        "d = max(abs(y - z));"
        "mid = max(abs(y(1621:1980)));"
    )
    b, a = g("b").reshape(-1), g("a").reshape(-1)
    assert _mag(b, a, 0.5, 360) == pytest.approx(1 / np.sqrt(2), abs=1e-6)
    assert _mag(b, a, 40, 360) == pytest.approx(1 / np.sqrt(2), abs=1e-6)
    assert _mag(b, a, 10, 360) == pytest.approx(0.999310, abs=1e-5)
    assert _mag(b, a, 0.05, 360) < 0.02
    assert _mag(b, a, 100, 360) < 0.1
    assert _mag(b, a, 180, 360) < 1e-6
    assert g("d").reshape(-1)[0] == 0.0
    # filtfilt applies |H|^2. The 10 Hz tone stays near unit amplitude.
    assert g("mid").reshape(-1)[0] == pytest.approx(_mag(b, a, 10, 360) ** 2, abs=1e-3)


def test_bandpass_rejects_bad_edges(run):
    with pytest.raises(EvalError):
        run("bandpass(ones(1, 64), [40 0.5], 360);")
    with pytest.raises(EvalError):
        run("filtfilt([0.5 0.5], 1, 1:3);")
    with pytest.raises(EvalError):
        run("butter(2, [0.5 40]);")
