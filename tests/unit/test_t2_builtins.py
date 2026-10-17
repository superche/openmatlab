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


def test_batch3_misc():
    assert bool(ev("r = isuniform(1:5);").item()) is True
    assert bool(ev("r = isuniform([1 2 4]);").item()) is False
    np.testing.assert_allclose(ev("r = vecnorm([3 4; 0 0]);"), [[3, 4]])
    np.testing.assert_allclose(ev("r = vecnorm([3 4; 0 0], 2, 2);"), [[5], [0]])
    np.testing.assert_array_equal(ev("r = sinpi([0 0.5 1 1.5]);"), [[0, 1, 0, -1]])
    np.testing.assert_array_equal(ev("r = cospi([0 0.5 1 1.5]);"), [[1, 0, -1, 0]])
    np.testing.assert_allclose(ev("r = polyarea([0 1 1 0], [0 0 1 1]);"), [[1]])
    assert ev("r = pagetranspose(ones(2, 3, 4));").shape == (3, 2, 4)
    assert ev("r = swapbytes(uint16(1));").item() == 256
    np.testing.assert_allclose(ev("r = rectint([0 0 1 1], [0.5 0.5 1 1]);"), [[0.25]])
    np.testing.assert_allclose(ev("r = subspace([1; 0], [0; 1]);"), [[np.pi / 2]])
    np.testing.assert_allclose(ev("r = uniquetol([1 1+1e-14 2]);"), [[1, 2]])
    np.testing.assert_array_equal(ev("r = ismembertol([1 2 3], [1+1e-14 3]);"), [[True, False, True]])
    np.testing.assert_allclose(ev("r = movmad([1 2 4 8], 3);"), [[0.5, 1, 2, 2]])


def test_mode_var_outputs():
    np.testing.assert_allclose(ev("[m, f, c] = mode([1 2 2 3 3]); r = c{1};"), [[2], [3]])
    np.testing.assert_allclose(ev("[v, r] = var([1 2 3 4]);"), [[2.5]])
    np.testing.assert_allclose(ev("r = var([1 2; 3 4], 0, [1 2]);"), [[np.var([1, 2, 3, 4], ddof=1)]])
    assert ev("r = median(single([1 2 3]));").dtype == np.float32


def test_incomplete_gamma_beta_expint():
    import math
    np.testing.assert_allclose(ev("r = gammainc([0.5 2 10], 2);"), [[1 - math.exp(-x) * (1 + x) for x in (0.5, 2, 10)]],
                               rtol=1e-14)
    np.testing.assert_allclose(ev("r = gammainc(3, 2, 'upper');"), [[4 * math.exp(-3)]], rtol=1e-14)
    np.testing.assert_allclose(ev("r = gammainc(3, 2, 'scaledupper');"), [[8 / 9]], rtol=1e-14)
    np.testing.assert_allclose(ev("r = gammainc(-1, 2);"), [[1.0]], atol=1e-14)  # 1 - exp(1) * (1 + (-1))
    np.testing.assert_array_equal(ev("r = gammainc([0 0 1], [0 1 0]);"), [[1, 0, 1]])
    np.testing.assert_allclose(ev("r = gammainc(gammaincinv([0.1 0.5 0.9], 2.5), 2.5);"), [[0.1, 0.5, 0.9]], rtol=1e-12)
    np.testing.assert_allclose(ev("r = betainc(0.3, 2, 3);"), [[1 - (0.7 ** 4 + 4 * 0.3 * 0.7 ** 3)]], rtol=1e-14)
    np.testing.assert_allclose(ev("r = betainc(0.3, 2, 3, 'upper');"), [[0.7 ** 4 + 4 * 0.3 * 0.7 ** 3]], rtol=1e-14)
    np.testing.assert_allclose(ev("r = betaincinv(0.3483, 2, 3);"), [[0.3]], rtol=1e-12)
    np.testing.assert_allclose(ev("r = betaln(2, 3);"), [[math.log(1 / 12)]], rtol=1e-14)
    np.testing.assert_allclose(ev("r = expint(1);"), [[0.21938393439552029]], rtol=1e-14)
    r = ev("r = expint(-1);")
    np.testing.assert_allclose(r, [[-1.8951178163559368 - 1j * math.pi]], rtol=1e-14)
    assert ev("r = gammainc(single(1), 2);").dtype == np.float32
