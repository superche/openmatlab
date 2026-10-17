"""Moving statistics (C-E5 #765 T2): normalisation weight, SamplePoints, movmax/movmin NaN default."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession

pytestmark = [pytest.mark.unit]


def ev(code, name="r"):
    s = ReplSession()
    s.run_line(code)
    return np.asarray(s.session.workspace.get(name).backend_buffer())


def test_movvar_movstd_weight_then_dim():
    np.testing.assert_allclose(ev("r = movvar([2 4 8], 3, 1);"), [[1, 56 / 9, 4]])
    np.testing.assert_allclose(ev("r = movvar([2 4 8], 3, []);"), [[2, 28 / 3, 8]])
    np.testing.assert_allclose(ev("r = movstd([1 3; 5 9], 2, 0, 2);"), [[0, np.sqrt(2)], [0, np.sqrt(8)]])
    np.testing.assert_allclose(ev("r = movvar([1 2 3], 3, 0, 1);"), [[0, 0, 0]])


def test_sample_points_windows():
    # window [t - k/2, t + k/2): with t = [0 1 3 4], k = 2 covers t-1 .. t (excluding t+1)
    np.testing.assert_allclose(ev("r = movsum([1 2 3 4], 2, 'SamplePoints', [0 1 3 4]);"), [[1, 3, 3, 7]])
    np.testing.assert_allclose(ev("r = movmean([1 2 3 4], [1 1], 'SamplePoints', [0 1 3 4]);"), [[1.5, 1.5, 3.5, 3.5]])


def test_movmax_movmin_omit_nan_by_default():
    np.testing.assert_allclose(ev("r = movmax([1 NaN 3], 3);"), [[1, 3, 3]])
    np.testing.assert_allclose(ev("r = movmin([NaN 2 1], 2);"), [[np.nan, 2, 1]])
    assert np.isnan(ev("r = movmax([1 NaN 3], 3, 'includenan');")).tolist() == [[True, True, True]]
