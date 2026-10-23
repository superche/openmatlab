"""smoothdata movmean and gaussian (M14 V-E2, Epic #995)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return lambda n: s.workspace.get(n)


def _n(v):
    return np.asarray(v.backend_buffer())


def _ref_gaussian(y, window, sp=None, omit=True):
    """Public window rule, independent of the builtin.

    Scalar ``k`` keeps sample points in ``[t-k/2, t+k/2)`` and uses ``sigma = k/5``.
    ``[b f]`` keeps ``[t-b, t+f]`` and uses ``sigma = (b+f+1)/5``. Default sample
    points are ``1:n``. Weights ``exp(-1/2 (d/sigma)^2)`` are rescaled on the
    samples that remain after truncation and, when requested, NaN omission.
    """
    y = np.asarray(y, dtype=float).reshape(-1)
    n = y.size
    pts = np.arange(1, n + 1, dtype=float) if sp is None else np.asarray(sp, dtype=float).reshape(-1)
    wspec = np.asarray(window, dtype=float).reshape(-1)
    if wspec.size == 1:
        k = float(wspec[0])
        sigma, lo, hi, closed = k / 5.0, pts - k / 2.0, pts + k / 2.0, False
    else:
        b, f = float(wspec[0]), float(wspec[1])
        sigma, lo, hi, closed = (b + f + 1.0) / 5.0, pts - b, pts + f, True
    out = np.empty(n)
    for i in range(n):
        mask = (pts >= lo[i]) & (pts <= hi[i] if closed else pts < hi[i])
        sl, d = y[mask], pts[mask] - pts[i]
        wt = np.exp(-0.5 * (d / sigma) ** 2)
        if omit:
            ok = ~np.isnan(sl)
            sl, wt = sl[ok], wt[ok]
        elif np.any(np.isnan(sl)):
            out[i] = np.nan
            continue
        out[i] = np.dot(wt, sl) / wt.sum() if wt.size else np.nan
    return out


def test_movmean_method_matches_movmean():
    g = _ws(
        "a = smoothdata(1:6, 'movmean', 4); b = movmean(1:6, 4);"
        " c = smoothdata([1 2; 3 4; 5 6], 'movmean', 2); d = movmean([1 2; 3 4; 5 6], 2);"
        " e = smoothdata([1 2 3 4 5], 2, 'movmean', [1 0]); f = movmean([1 2 3 4 5], [1 0], 2);"
        " p = smoothdata([1 2 3 4], 'movmean', [1 1], 'SamplePoints', [0 1 3 4]);"
        " q = movmean([1 2 3 4], [1 1], 'SamplePoints', [0 1 3 4]);"
        " col = size(smoothdata((1:6)', 'movmean', 3));"
    )
    assert np.array_equal(_n(g("a")), _n(g("b")))
    assert np.allclose(_n(g("a")), [[1.5, 2, 2.5, 3.5, 4.5, 5]])
    assert np.array_equal(_n(g("c")), _n(g("d")))
    assert np.array_equal(_n(g("e")), _n(g("f")))
    assert np.array_equal(_n(g("p")), _n(g("q")))
    assert np.allclose(_n(g("col")), [[6, 1]])


def test_movmean_nanflag_defaults_to_omitnan():
    g = _ws(
        "x = [1 NaN 3 5]; a = smoothdata(x, 'movmean', 3); b = movmean(x, 3, 'omitnan');"
        " c = smoothdata(x, 'movmean', 3, 'includenan'); d = movmean(x, 3);"
        " e = smoothdata(x, 'omitmissing', 'movmean', 3);"
    )
    assert np.allclose(_n(g("a")), _n(g("b")))
    assert np.allclose(_n(g("a")), [[1, 2, 4, 4]])
    assert np.array_equal(np.isnan(_n(g("c"))), np.isnan(_n(g("d"))))
    assert np.isnan(_n(g("c"))).tolist() == [[True, True, True, False]]
    assert np.allclose(_n(g("e")), _n(g("a")))


def test_gaussian_matches_public_window_formula():
    y = np.array([1.0, 2, 10, 2, 1])
    g = _ws("y = [1 2 10 2 1]; a = smoothdata(y, 'gaussian', 3); b = smoothdata(y, 'gaussian', 4);"
            " c = smoothdata(y', 'gaussian', [1 1]); d = smoothdata([5 5 5 5], 'gaussian', 5);")
    assert np.allclose(_n(g("a")).reshape(-1), _ref_gaussian(y, 3))
    assert np.allclose(_n(g("b")).reshape(-1), _ref_gaussian(y, 4))
    assert np.allclose(_n(g("c")).reshape(-1), _ref_gaussian(y, [1, 1]))
    assert _n(g("c")).shape == (5, 1)
    assert np.allclose(_n(g("d")), [[5, 5, 5, 5]])


def test_gaussian_sample_points_and_nan_and_spike():
    y = np.array([1.0, 2, 10, 4])
    sp = np.array([0.0, 1, 3, 4])
    nan = np.array([1.0, np.nan, 3, 4])
    g = _ws(
        "y = [1 2 10 4]; sp = [0 1 3 4]; a = smoothdata(y, 'gaussian', 2, 'SamplePoints', sp);"
        " b = smoothdata([1 NaN 3 4], 'gaussian', 3); c = smoothdata([1 NaN 3 4], 'gaussian', 3, 'includenan');"
        " x = [0 0 0 10 0 0 0]; g3 = smoothdata(x, 'gaussian', 3); g7 = smoothdata(x, 'gaussian', 7);"
        " [s, w] = smoothdata(1:4, 'gaussian', [2 1]);"
    )
    assert np.allclose(_n(g("a")).reshape(-1), _ref_gaussian(y, 2, sp=sp))
    assert np.allclose(_n(g("b")).reshape(-1), _ref_gaussian(nan, 3, omit=True))
    assert np.allclose(_n(g("c")).reshape(-1), _ref_gaussian(nan, 3, omit=False), equal_nan=True)
    g3, g7 = float(_n(g("g3")).reshape(-1)[3]), float(_n(g("g7")).reshape(-1)[3])
    assert 0 < g7 < g3 < 10
    assert np.allclose(_n(g("w")), [[2, 1]])
    assert np.allclose(_n(g("s")).reshape(-1), _ref_gaussian(np.arange(1, 5), [2, 1]))


def test_window_required_and_methods_outside_the_slice():
    g = _ws(
        "try, smoothdata(1:5, 'movmean'); m = ''; catch err, m = err.identifier; end;"
        " try, smoothdata(1:5, 'lowess', 5); m2 = ''; catch err, m2 = err.identifier; end;"
        " try, smoothdata(1:5, 'sgolay', 5); m3 = ''; catch err, m3 = err.identifier; end;"
        " try, smoothdata(1:5, 'gaussian', 3, 'SmoothingFactor', 0.5); m4 = ''; catch err, m4 = err.identifier; end;"
        " try, T = table((1:4)', 'VariableNames', {'a'}); smoothdata(T, 'movmean', 3); m5 = ''; catch err, m5 = err.identifier; end;"
        " try, smoothdata(1:4, 'movmean', 0); m6 = ''; catch err, m6 = err.identifier; end;"
    )
    assert g("m").text == "OpenMATLAB:smoothdata:WindowRequired"
    assert g("m2").text == "OpenMATLAB:smoothdata:UnsupportedMethod"
    assert g("m3").text == "OpenMATLAB:smoothdata:UnsupportedMethod"
    assert g("m4").text == "OpenMATLAB:smoothdata:UnsupportedOption"
    assert g("m5").text == "OpenMATLAB:smoothdata:Table"
    assert g("m6").text == "MATLAB:smoothdata:invalidWindow"
