"""Epic #534: core math, statistics, random numbers, timing and numeric helpers."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer())


def _c(s, n):
    return s.workspace.get(n).matlab_class()


def test_fix_rem_mod_sign():
    s = _run("a = fix([-2.5 2.5 -0.5]); b = rem([5 -5 5], [3 3 0]); c = sign([-2 0 3]); d = rem(5, Inf); e = sign(3+4i);")
    assert _v(s, "a").tolist() == [[-2, 2, -0.0]] and _v(s, "c").tolist() == [[-1, 0, 1]]
    b = _v(s, "b")[0]
    assert b[0] == 2 and b[1] == -2 and np.isnan(b[2]) and _v(s, "d").item() == 5
    assert np.isclose(_v(s, "e").item(), 0.6 + 0.8j)


def test_integer_classes_preserved_and_saturated():
    s = _run("a = rem(int8(7), int8(3)); b = cumprod(int8([2 3 4 5 6])); c = round(int16(7), -1);")
    assert _c(s, "a") == "int8" and _v(s, "a").item() == 1
    assert _v(s, "b").tolist() == [[2, 6, 24, 120, 127]] and _c(s, "c") == "int16" and _v(s, "c").item() == 10


def test_log2_two_outputs_and_negative():
    s = _run("[f, e] = log2([8 0.75]); z = log2(-4);")
    assert _v(s, "f").tolist() == [[0.5, 0.75]] and _v(s, "e").tolist() == [[4, 0]]
    assert np.isclose(_v(s, "z").item(), 2 + np.pi / np.log(2) * 1j)


def test_nthroot_real_and_error():
    s = _run("a = nthroot(-27, 3); b = nthroot(16, 4);")
    assert _v(s, "a").item() == -3 and _v(s, "b").item() == 2
    with pytest.raises(EvalError, match="odd integer"):
        _run("nthroot(-16, 4)")


def test_diff_orders_and_dims():
    s = _run("a = diff([1 4 9 16], 2); b = diff([1 2; 4 8]); c = diff([1 2; 4 8], 1, 2); d = diff(5);")
    assert _v(s, "a").tolist() == [[2, 2]] and _v(s, "b").tolist() == [[3, 6]]
    assert _v(s, "c").tolist() == [[1], [4]] and _v(s, "d").size == 0


def test_cumulative_ops():
    s = _run("a = cumprod([1 2 3 4]); b = cummax([1 3 2 5]); c = cummin([3 1 2], 'reverse'); d = cumprod([1 2; 3 4], 2);")
    assert _v(s, "a").tolist() == [[1, 2, 6, 24]] and _v(s, "b").tolist() == [[1, 3, 3, 5]]
    assert _v(s, "c").tolist() == [[1, 1, 2]] and _v(s, "d").tolist() == [[1, 2], [3, 12]]


def test_number_theory():
    s = _run("a = gcd([12 7], [18 0]); b = lcm(int32(4), 6); c = isprime([0 1 2 97 100]); d = nchoosek(30, 15); e = factorial([0 1 5 171]);")
    assert _v(s, "a").tolist() == [[6, 7]] and _v(s, "b").item() == 12
    assert _v(s, "c").tolist() == [[False, False, True, True, False]] and _v(s, "d").item() == 155117520
    assert _v(s, "e").tolist()[0][:3] == [1, 1, 120] and np.isinf(_v(s, "e")[0, 3])
    with pytest.raises(EvalError):
        _run("factorial(-1)")


def test_round_digits_and_significant():
    s = _run("a = round(2.675, 2); b = round(1234.5, -2); c = round(0.012345, 3, 'significant'); d = round(-2.5);")
    assert _v(s, "a").item() == 2.68 and _v(s, "b").item() == 1200
    assert np.isclose(_v(s, "c").item(), 0.0123) and _v(s, "d").item() == -3


def test_median_mode_with_nan_and_dims():
    s = _run("a = median([1 NaN 3]); b = median([1 NaN 3], 'omitnan'); c = median([1 2; 3 4], 2); [m, f] = mode([3 3 1 1 2]); e = median([]);")
    assert np.isnan(_v(s, "a").item()) and _v(s, "b").item() == 2 and _v(s, "c").tolist() == [[1.5], [3.5]]
    assert _v(s, "m").item() == 1 and _v(s, "f").item() == 2 and np.isnan(_v(s, "e").item())


def test_var_std_weights_dims():
    s = _run("a = var([1 2 3 4], 1); b = std([1 2; 3 6], 0, 2); c = var([1 2 3], [1 1 2]); d = var(5); e = std([1 NaN 3], 'omitnan');")
    assert _v(s, "a").item() == 1.25 and np.allclose(_v(s, "b").ravel(), [np.sqrt(0.5), np.sqrt(4.5)])
    assert np.isclose(_v(s, "c").item(), 0.6875) and _v(s, "d").item() == 0 and np.isclose(_v(s, "e").item(), np.sqrt(2))
    with pytest.raises(EvalError):
        _run("var([1 2], 3)")


def test_cov_corrcoef_range_bounds():
    s = _run("C = cov([1 2 3], [1 2 4]); R = corrcoef([1 2 3], [3 2 1]); r = range([4 9 1]); [lo, hi] = bounds([4 9 1]);")
    assert np.allclose(_v(s, "C"), np.cov([1, 2, 3], [1, 2, 4])) and np.allclose(_v(s, "R"), [[1, -1], [-1, 1]])
    assert _v(s, "r").item() == 8 and _v(s, "lo").item() == 1 and _v(s, "hi").item() == 9


def test_rng_reproducible_and_matches_matlab_default():
    s = _run("rng(0); a = rand(2, 2); rng(42); b = rand(1, 3); rng(42); c = rand(1, 3); st = rng; d = rand; rng(st); e = rand;")
    assert np.allclose(_v(s, "a"), [[0.8147236863931789, 0.1269868162935061], [0.9057919370756192, 0.9133758561390194]])
    assert np.allclose(_v(s, "b"), [[0.3745401188473625, 0.9507143064099162, 0.7319939418114051]])
    assert np.array_equal(_v(s, "b"), _v(s, "c")) and _v(s, "d").item() == _v(s, "e").item()


def test_rand_shapes_and_classes():
    s = _run("a = rand(3); b = rand([2 4]); c = rand(2, 'single'); d = randn(0, 3); e = randi([5 7], 2, 3); f = randperm(6, 3);")
    assert _v(s, "a").shape == (3, 3) and _v(s, "b").shape == (2, 4) and _c(s, "c") == "single"
    assert _v(s, "d").shape == (0, 3) and _v(s, "e").shape == (2, 3) and set(np.unique(_v(s, "e"))) <= {5, 6, 7}
    f = _v(s, "f").ravel()
    assert f.size == 3 and len(set(f)) == 3 and set(f) <= set(range(1, 7))


def test_rng_bad_seed():
    with pytest.raises(EvalError, match="seed"):
        _run("rng(-1)")


def test_tic_toc_statement_and_value(capsys):
    _run("tic; toc")
    assert "Elapsed time is" in capsys.readouterr().out
    s = _run("t = tic; pause(0.01); e = toc(t);")
    assert _c(s, "t") == "uint64" and 0.005 < _v(s, "e").item() < 5


def test_toc_without_tic_errors():
    from openmatlab.libs import math_builtins as mb

    mb._TIC["t"] = None
    with pytest.raises(EvalError, match="TIC"):
        _run("e = toc;")


def test_isnan_family_and_degree_trig():
    s = _run("a = isnan([1 NaN Inf]); b = isinf([1 NaN -Inf]); c = isfinite(int8(3)); d = sind([0 30 180 270]); e = cosd(90); f = tand(45); g = atan2(1, 1);")
    assert _v(s, "a").tolist() == [[False, True, False]] and _v(s, "b").tolist() == [[False, False, True]]
    assert _v(s, "c").tolist() == [[True]] and np.allclose(_v(s, "d"), [[0, 0.5, 0, -1]]) and _v(s, "d")[0, 2] == 0
    assert _v(s, "e").item() == 0 and _v(s, "f").item() == 1 and np.isclose(_v(s, "g").item(), np.pi / 4)


def test_vectors_and_integration():
    s = _run("a = cross([1 0 0], [0 1 0]); b = dot([1 2 3], [4 5 6]); k = kron([1 2], [1; 1]); t = trapz([1 2 3]); c = cumtrapz([1 2 3]); t2 = trapz([0 1 3], [0 1 3]);")
    assert _v(s, "a").tolist() == [[0, 0, 1]] and _v(s, "b").item() == 32 and _v(s, "k").tolist() == [[1, 2], [1, 2]]
    assert _v(s, "t").item() == 4 and _v(s, "c").tolist() == [[0, 1.5, 4]] and _v(s, "t2").item() == 4.5


def test_polynomials():
    s = _run("p = polyfit([0 1 2], [1 3 7], 2); r = roots([1 -3 2]); [q, rr] = deconv([1 0 -1], [1 1]); c = conv([1 2 3], [1 1], 'same');")
    assert np.allclose(_v(s, "p"), [[1, 1, 1]]) and np.allclose(sorted(_v(s, "r").ravel()), [1, 2])
    assert np.allclose(_v(s, "q"), [[1, -1]]) and np.allclose(_v(s, "rr"), [[0, 0, 0]]) and _v(s, "c").tolist() == [[3, 5, 3]]


def test_filter_interp1_hist_accum():
    s = _run("[y, zf] = filter([1 1], 1, [1 2 3]); a = interp1([1 2 3], [10 20 30], [1.5 2.5 9]); b = interp1([1 2 3], [10 20 30], 4, 'linear', 'extrap');"
             " n = interp1([1 2 3], [10 20 30], 2.5, 'nearest'); h = histcounts([1 2 2 3 5], [0 2 4 6]); A = accumarray([1 1; 2 2; 1 1], [1 2 3]);")
    assert _v(s, "y").tolist() == [[1, 3, 5]] and _v(s, "zf").ravel().tolist() == [3]
    a = _v(s, "a")[0]
    assert a[0] == 15 and a[1] == 25 and np.isnan(a[2]) and _v(s, "b").item() == 40 and _v(s, "n").item() == 30
    assert _v(s, "h").tolist() == [[1, 3, 1]] and _v(s, "A").tolist() == [[4, 0], [0, 2]]


def test_function_functions():
    s = _run("x = fzero(@(x) cos(x) - x, [0 1]); y = fzero(@(x) x.^3 - 8, 1); m = fminsearch(@(p) (p(1)-3).^2 + (p(2)+1).^2, [0 0]); q = integral(@(x) x.^2, 0, 3); g = integral(@(x) exp(-x.^2), -Inf, Inf);")
    assert np.isclose(_v(s, "x").item(), 0.7390851332) and np.isclose(_v(s, "y").item(), 2)
    assert np.allclose(_v(s, "m"), [[3, -1]], atol=1e-3) and np.isclose(_v(s, "q").item(), 9)
    assert np.isclose(_v(s, "g").item(), np.sqrt(np.pi), atol=1e-6)
    with pytest.raises(EvalError, match="differ in sign"):
        _run("fzero(@(x) x.^2 + 1, [0 1])")
