"""T2 burn-down builtins (C-E5 #765): documented MATLAB behaviour, own examples."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession

pytestmark = [pytest.mark.unit]


def ev(code, name="r"):
    s = ReplSession()
    s.run_line(code)
    return np.asarray(s.session.workspace.get(name).backend_buffer())


@pytest.mark.parametrize("code,want", [
    ("r = issymmetric([1 2; 2 1]);", True),
    ("r = issymmetric([1 2; 3 1]);", False),
    ("r = issymmetric([0 2; -2 0], 'skew');", True),
    ("r = ishermitian([1 2i; -2i 1]);", True),
    ("r = isdiag(diag([1 2 3]));", True),
    ("r = istril([1 0; 2 3]);", True),
    ("r = istriu([1 0; 2 3]);", False),
    ("r = isbanded([1 2 0; 3 4 5; 0 6 7], 1, 1);", True),
])
def test_structure_predicates(code, want):
    assert bool(ev(code).item()) is want


def test_bandwidth():
    assert ev("[r, u] = bandwidth([1 2 0; 3 4 5; 0 6 7]);").item() == 1
    assert ev("r = bandwidth(ones(4), 'upper');").item() == 3


def test_data_metrics():
    np.testing.assert_allclose(ev("r = rms([3 4]);"), [[np.sqrt(12.5)]])
    np.testing.assert_allclose(ev("r = rmse([1 2 3], [1 2 5]);"), [[np.sqrt(4 / 3)]])
    np.testing.assert_allclose(ev("r = mape([1 2], [2 2]);"), [[25.0]])
    np.testing.assert_allclose(ev("r = rmse([1 2; 3 4], [1 2; 3 6], 'all');"), [[1.0]])
    np.testing.assert_allclose(ev("r = rescale(1:4, 3, 9);"), [[3, 5, 7, 9]])


def test_coordinates():
    np.testing.assert_allclose(ev("[t, r] = cart2pol(1, 1);", "r"), [[np.sqrt(2)]])
    np.testing.assert_allclose(ev("[x, r] = pol2cart(pi/2, 2);", "r"), [[2.0]], atol=1e-12)
    np.testing.assert_allclose(ev("[x, y, r] = sph2cart(0, pi/2, 3);", "r"), [[3.0]])
    np.testing.assert_allclose(ev("[az, el, r] = cart2sph(0, 0, 2);", "r"), [[2.0]])


def test_bits_dates_paths():
    assert ev("r = bitcmp(uint8(0));").item() == 255
    assert ev("r = bitset(0, 3);").item() == 4
    assert ev("r = bitset(uint8(255), 1, 0);").item() == 254
    np.testing.assert_array_equal(ev("r = eomday([2000 1900 2023], 2);"), [[29, 28, 28]])
    assert ev("r = double(erase('hello world', 'o'));").tobytes() == np.array([[ord(c) for c in "hell wrld"]], float).tobytes()


def test_tensorprod():
    np.testing.assert_allclose(ev("A = [1 2; 3 4]; r = tensorprod(A, A, 2);"), [[5, 11], [11, 25]])
    np.testing.assert_allclose(ev("r = tensorprod([1 2], [1 2], 'all');"), [[5]])
    assert ev("r = tensorprod([1 2], [1 2]);").shape == (1, 2, 1, 2)


def test_normalize():
    np.testing.assert_allclose(ev("r = normalize([1 2 3]);"), [[-1, 0, 1]])
    np.testing.assert_allclose(ev("r = normalize([1 2 3], 'range');"), [[0, 0.5, 1]])
    np.testing.assert_allclose(ev("r = normalize([1 2 3], 'norm', 1);"), [[1 / 6, 1 / 3, 1 / 2]])
    np.testing.assert_allclose(ev("r = normalize([1 2 3], 'center', 'median');"), [[-1, 0, 1]])
    np.testing.assert_allclose(ev("r = normalize([1 2 3], 'scale', 'iqr');"), [[2 / 3, 4 / 3, 2]])


def test_datevec():
    np.testing.assert_allclose(ev("r = datevec('07-Sep-2000 15:38:09');"), [[2000, 9, 7, 15, 38, 9]])
    np.testing.assert_allclose(ev("r = datevec(datenum(2014, 6, 18, 12, 30, 15));"), [[2014, 6, 18, 12, 30, 15]], atol=1e-6)
    np.testing.assert_allclose(ev("r = datevec(1);"), [[0, 1, 1, 0, 0, 0]])
    np.testing.assert_allclose(ev("r = datevec('06/01/2015 3:07:12.102 PM', 'mm/dd/yyyy HH:MM:SS.FFF PM');"),
                               [[2015, 6, 1, 15, 7, 12.102]])
    np.testing.assert_allclose(ev("[~, ~, r] = datevec([1 2; 3 4]);"), [[1, 2], [3, 4]])
