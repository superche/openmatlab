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


def test_gallery_families():
    np.testing.assert_array_equal(ev("r = gallery('minij', 3);"), [[1, 1, 1], [1, 2, 2], [1, 2, 3]])
    np.testing.assert_array_equal(ev("r = gallery('clement', 3);"), [[0, 1, 0], [2, 0, 2], [0, 1, 0]])
    np.testing.assert_array_equal(ev("r = gallery('circul', [1 3 6]);"), [[1, 3, 6], [6, 1, 3], [3, 6, 1]])
    np.testing.assert_allclose(ev("r = gallery('cauchy', 1:2);"), [[1 / 2, 1 / 3], [1 / 3, 1 / 4]])
    np.testing.assert_array_equal(ev("r = gallery('fiedler', 3);"), [[0, 1, 2], [1, 0, 1], [2, 1, 0]])
    np.testing.assert_array_equal(ev("r = gallery('tridiag', 3);"), [[2, -1, 0], [-1, 2, -1], [0, -1, 2]])
    assert ev("r = gallery('poisson', 3);").shape == (9, 9)
    np.testing.assert_allclose(ev("A = gallery('invol', 4); r = A*A;"), np.eye(4), atol=1e-9)
    np.testing.assert_allclose(ev("Q = gallery('orthog', 5, 2); r = Q*Q';"), np.eye(5), atol=1e-12)
    np.testing.assert_allclose(ev("x = [3; 4]; [v, b] = gallery('house', x); r = (eye(2) - b*(v*v'))*x;"),
                               [[-5], [0]], atol=1e-12)
    np.testing.assert_allclose(ev("r = sum(gallery('chebspec', 5), 2);"), np.zeros((5, 1)), atol=1e-12)
    assert ev("r = gallery('randsvd', [5 3]);").shape == (5, 3)
    s = ReplSession()
    s.run_line("try, gallery('nosuch', 3); r = 0; catch err, r = strcmp(err.identifier, 'MATLAB:gallery:unknownName'); end")
    assert bool(np.asarray(s.session.workspace.get("r").backend_buffer()).item())


def test_dec2bin_dec2hex_negative_and_addtodate():
    s = ReplSession()
    s.run_line("a = dec2bin(-3); b = dec2hex(-129); c = dec2bin([1 -4]); d = dec2bin(2.9);")
    w = s.session.workspace
    assert w.get("a").text == "11111101"
    assert w.get("b").text == "FF7F"
    assert list(w.get("c").rows) == ["00000001", "11111100"]
    assert w.get("d").text == "10"
    np.testing.assert_allclose(ev("d = datenum(2008, 1, 1); r = addtodate(d, [1 13], 'month') - d;"), [[31, 397]])
    np.testing.assert_allclose(ev("r = addtodate(datenum(2020, 3, 31), -1, 'month') - datenum(2020, 2, 29);"), [[0]])
    np.testing.assert_allclose(ev("r = addtodate(10, 6, 'hour');"), [[10.25]])


def test_interp1_matrix_methods_pp():
    np.testing.assert_allclose(ev("r = interp1([1 2 3], [10 20; 20 40; 30 60], [1.5 2.5]);"), [[15, 30], [25, 50]])
    np.testing.assert_allclose(ev("r = interp1([1 2 3], [1 4 9], 4, 'linear', 'extrap');"), [[14]])
    np.testing.assert_allclose(ev("r = interp1([1 2 3], [1 4 9], 4, 'linear', 0);"), [[0]])
    assert np.isnan(ev("r = interp1([1 2 3], [1 4 9], 4);")).all()
    np.testing.assert_allclose(ev("r = interp1([1 2 3 4], [1 8 27 64], 5, 'spline');"), [[125]], rtol=1e-12)
    np.testing.assert_allclose(ev("r = interp1([1 2 3], [5 6 7], [1.2 2.6], '*nearest');"), [[5, 7]])
    np.testing.assert_allclose(ev("r = interp1([3 2 1], [9 4 1], 1.5);"), [[2.5]])
    np.testing.assert_allclose(ev("r = interp1([1 2 3], [1 2 3] + 1i, 2.5);"), [[2.5 + 1j]])
    np.testing.assert_allclose(ev("r = ppval(interp1([1 2 3], [1 4 9], 'linear', 'pp'), 2.5);"), [[6.5]])
    np.testing.assert_allclose(ev("r = interp1([1 2 3 4 5], [1 2 3 4 5], 2.5, 'makima');"), [[2.5]], rtol=1e-12)


def test_continuation_after_name_is_not_command_syntax():
    np.testing.assert_allclose(ev("r = max ...\n  (3, 4);"), [[4]])
    s = ReplSession()
    s.run_line("x = 1;\nassert ...\n  (x == 1, 'msg');\nr = 2;")
    assert np.asarray(s.session.workspace.get("r").backend_buffer()).item() == 2


def test_mean_median_options():
    np.testing.assert_allclose(ev("r = mean(magic(4), [1 2]);"), [[8.5]])
    assert ev("r = mean(uint8([1 2 4]), 'native');").dtype == np.uint8
    assert ev("r = mean(uint8([1 2 4]), 'native');").item() == 2
    assert ev("r = mean(int64([intmin('int64') intmax('int64')-1]));").item() == -1.0
    assert ev("r = mean(single([1 2]), 'double');").dtype == np.float64
    np.testing.assert_allclose(ev("r = mean([1 NaN 3], 'omitnan');"), [[2]])
    np.testing.assert_allclose(ev("r = mean([1 1; 7 9], 'Weights', [1; 3]);"), [[5.5, 7]])
    assert np.isnan(ev("r = mean([]);")).all()
    assert ev("r = median(int8([1 2]));").dtype == np.int8
    assert ev("r = median(uint8([253 255]));").item() == 254
    np.testing.assert_allclose(ev("r = median([3 1 NaN 2], 'omitnan');"), [[2]])
    np.testing.assert_allclose(ev("r = median(magic(3), [1 99]);"), [[4, 5, 6]])


def test_mode_options_and_empties():
    s = ReplSession()
    s.run_line("[m, f, c] = mode([1 2 2 3 3 NaN]);")
    w = s.session.workspace
    assert np.asarray(w.get("m").backend_buffer()).item() == 2
    assert np.asarray(w.get("f").backend_buffer()).item() == 2
    np.testing.assert_array_equal(np.asarray(w.get("c").get(0, 0).backend_buffer()), [[2], [3]])
    np.testing.assert_array_equal(ev("r = mode(magic(3) > 4, 'all');"), [[True]])
    np.testing.assert_array_equal(ev("r = mode([1 1; 2 2; 2 1], [1 2]);"), [[1]])
    assert np.isnan(ev("r = mode([]);")).all()
    assert ev("r = mode(int8([3 3 1]));").dtype == np.int8


def test_var_weight_array_and_large_dims():
    np.testing.assert_allclose(ev("r = var(3*magic(3), ones(3,3));"), [[42, 96, 42]])
    np.testing.assert_allclose(ev("r = var(magic(3), [], [1 99]);"), [[7, 16, 7]])
    np.testing.assert_array_equal(ev("r = var(ones(2,2,2), [], 99);"), np.zeros((2, 2, 2)))


def test_cov_flags_weights_and_classes():
    np.testing.assert_allclose(ev("r = cov([1 2 3 4 5], 1);"), [[2.0]])
    assert ev("r = cov(5, 0);").item() == 0
    np.testing.assert_allclose(ev("x = magic(3); x(3) = NaN; r = cov(x, 'omitrows');"),
                               [[12.5, -10, -2.5], [-10, 8, 2], [-2.5, 2, 0.5]])
    np.testing.assert_allclose(ev("x = magic(3); x(3) = NaN; r = cov(x, 'partialrows');"),
                               [[12.5, -10, -2.5], [-10, 16, -8], [-2.5, -8, 7]])
    assert ev("r = cov(5, single(0));").dtype == np.float64
    assert ev("r = cov(single([1 2 4]));").dtype == np.float32
    assert np.isnan(ev("r = cov([]);")).all()
    assert ev("r = cov(ones(2, 0));").size == 0


def test_sinint_cosint():
    np.testing.assert_allclose(ev("r = sinint([1 pi 300]);"), [[0.946083070367183, 1.851937051982466, 1.57088108821375]],
                               rtol=1e-14)
    np.testing.assert_allclose(ev("r = cosint([1 pi 300]);"), [[0.337403922900968, 0.0736679120464255, -0.00333219991859211]],
                               rtol=1e-13)
    np.testing.assert_allclose(ev("r = cosint(-1);"), [[0.337403922900968 + np.pi * 1j]], rtol=1e-14)
    np.testing.assert_allclose(ev("r = sinint(20i);"), [[1.2807826332028294e7j]], rtol=1e-14)
    assert ev("r = cosint(0);").item() == -np.inf
    assert ev("r = cosint(-0);").item() == complex(-np.inf, np.pi)
    assert ev("r = sinint(single(1));").dtype == np.float32


def test_unary_minus_and_complex_keep_signed_zero():
    assert np.signbit(ev("r = -0;")).all()
    assert np.signbit(ev("r = complex(1, -0);").imag).all()
    assert ev("r = 1/-0;").item() == -np.inf


def test_quadgk_and_integral():
    np.testing.assert_allclose(ev("r = quadgk(@(x) 1./sqrt(x), 0, 1);"), [[2.0]], rtol=1e-10)
    np.testing.assert_allclose(ev("r = quadgk(@(x) exp(-x.^2), -Inf, Inf);"), [[np.sqrt(np.pi)]], rtol=1e-10)
    np.testing.assert_allclose(ev("r = integral(@(x) 1./(x.^2 + 1), 0, Inf);"), [[np.pi / 2]], rtol=1e-10)
    np.testing.assert_allclose(ev("r = quadgk(@(z) 1./z, 1, 1, 'Waypoints', [1i, -1, -1i]);"), [[2j * np.pi]],
                               atol=1e-10)
    np.testing.assert_allclose(ev("r = integral(@(x) [x, x.^2], 0, 1, 'ArrayValued', true);"), [[0.5, 1 / 3]],
                               rtol=1e-10)
    assert ev("r = integral(@sin, single(0), 1);").dtype == np.float32
    assert ev("[q, r] = quadgk(@(x) x, 0, 1);").item() >= 0


def test_quadl_quadv():
    np.testing.assert_allclose(ev("r = quadl(@(x) x.^3, 0, 2);"), [[4.0]], rtol=1e-10)
    np.testing.assert_allclose(ev("r = quadl(@(x, c) c*x, 0, 1, [], [], 4);"), [[2.0]], rtol=1e-10)
    np.testing.assert_allclose(ev("r = quadv(@(x) [x; 2*x], 0, 1);"), [[0.5], [1.0]], rtol=1e-8)


def test_two_and_three_dimensional():
    np.testing.assert_allclose(ev("r = integral2(@(x, y) x.*y, 0, 1, 0, @(x) x);"), [[1 / 8]], rtol=1e-8)
    np.testing.assert_allclose(ev("r = quad2d(@(x, y) 1./(x + y), 0, 1, 0, 1);"), [[2 * np.log(2)]], rtol=1e-6)
    np.testing.assert_allclose(ev("r = integral3(@(x, y, z) x + y + z, 0, 1, 0, 2, 0, 3);"), [[18.0]], rtol=1e-8)
    np.testing.assert_allclose(ev("r = dblquad(@(x, y) x*y, 0, 1, 0, 2);"), [[1.0]], rtol=1e-6)
    np.testing.assert_allclose(ev("r = triplequad(@(x, y, z) x + 0*y*z, 0, 1, 0, 1, 0, 1);"), [[0.5]], rtol=1e-6)
