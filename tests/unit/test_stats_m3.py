"""Descriptive statistics: quantile/prctile, moving windows, histc (M3-E4, Epic #628)."""

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


def test_quantile_prctile_matlab_method_dims_and_nan():
    g = _ws("a = quantile([2 4 6 8 10], [0 0.1 0.25 1]); b = prctile([1 2; 3 4; 5 6], 50, 2);"
            " c = quantile([1 NaN 3], 0.5); d = quantile([1; 2; 3; 4], [0.25 0.75]); e = prctile(7, [10 90]);"
            " try, quantile(1:3, 1.5); m = ''; catch err, m = err.identifier; end")
    assert np.allclose(_n(g("a")), [[2, 2, 3.5, 10]])
    assert np.allclose(_n(g("b")), [[1.5], [3.5], [5.5]])
    assert _n(g("c"))[0, 0] == 2 and np.allclose(_n(g("d")), [[1.5], [3.5]]) and np.allclose(_n(g("e")), [[7, 7]])
    assert g("m").text == "MATLAB:quantile:BadPercents"


def test_moving_windows_endpoints_nan_and_dim():
    g = _ws("a = movmean(1:6, 4); b = movsum([1 2; 3 4; 5 6], 2); c = movmax([4 1 3 2], [0 1]);"
            " d = movmean([1 NaN 3], 3, 'omitnan'); e = movmean([1 NaN 3], 3); f = movsum(1:5, 3, 'Endpoints', 'discard');"
            " h = movmin(1:4, 3, 'Endpoints', 0); k = movmedian([1 2; 9 4; 3 8], 3, 2); v = movstd([1 2 4], 2);")
    assert np.allclose(_n(g("a")), [[1.5, 2, 2.5, 3.5, 4.5, 5]])
    assert np.allclose(_n(g("b")), [[1, 2], [4, 6], [8, 10]])
    assert np.allclose(_n(g("c")), [[4, 3, 3, 2]])
    assert np.allclose(_n(g("d")), [[1, 2, 3]]) and np.isnan(_n(g("e"))).tolist() == [[True, True, True]]
    assert np.allclose(_n(g("f")), [[6, 9, 12]]) and np.allclose(_n(g("h")), [[0, 1, 2, 0]])
    assert np.allclose(_n(g("k")), [[1.5, 1.5], [6.5, 6.5], [5.5, 5.5]])
    assert np.allclose(_n(g("v")), [[0, np.sqrt(0.5), np.sqrt(2)]])


def test_histc_counts_bins_and_matrix():
    g = _ws("[n, bin] = histc([0 1 1.5 3 4 9 NaN], [1 2 4]); m = histc([1 2; 2 3; 4 4], 1:4);")
    assert np.allclose(_n(g("n")), [[2, 1, 1]]) and np.allclose(_n(g("bin")), [[0, 1, 1, 2, 3, 0, 0]])
    assert np.allclose(_n(g("m")), [[1, 0], [1, 1], [0, 1], [1, 1]])
