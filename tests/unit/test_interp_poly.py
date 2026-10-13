"""Splines, pchip, ppval, interp1 methods, interp2, polyder, polyint (M3-E2, Epic #626)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return lambda n: np.asarray(s.workspace.get(n).backend_buffer())


def test_spline_not_a_knot_reproduces_cubics_and_clamped():
    g = _ws("x = 0:4; y = x.^3 - 2*x; a = spline(x, y, [0.5 2.5 3.7]); c = spline(0:2, [1 0 1 4 -1], 1);"
            " p = spline(0:2, [0 1 4], 1.5);")
    assert np.allclose(g("a"), [[0.5 ** 3 - 1, 2.5 ** 3 - 5, 3.7 ** 3 - 7.4]])
    assert np.isclose(g("c")[0, 0], 1.0) and np.isclose(g("p")[0, 0], 2.25)


def test_pp_struct_and_ppval_mkpp_unmkpp():
    g = _ws("pp = spline(0:3, [0 1 8 27]); f = pp.form; b = pp.breaks; o = pp.order; v = ppval(pp, [1 2.5]);"
            " q = mkpp([0 1 2], [1 0; 2 1]); w = ppval(q, [0.5 1.5]); [bb, cc] = unmkpp(q);")
    assert g("b").tolist() == [[0, 1, 2, 3]] and g("o")[0, 0] == 4
    assert np.allclose(g("v"), [[1, 15.625]]) and np.allclose(g("w"), [[0.5, 2.0]]) and g("cc").shape == (2, 2)


def test_pchip_shape_preserving():
    g = _ws("x = 1:6; y = [1 1 1 2 2 2]; v = pchip(x, y, 1:0.25:6); m = all(diff(v) >= -1e-12); e = pchip(0:3, (0:3).^3, [0 3]);")
    assert g("m")[0, 0] and g("v").min() >= 1 - 1e-12 and g("v").max() <= 2 + 1e-12
    assert np.allclose(g("e"), [[0, 27]])


def test_interp1_methods_extrapolate():
    g = _ws("x = 0:3; y = x.^3; a = interp1(x, y, 4, 'spline'); b = interp1(x, y, 1.5, 'cubic'); c = interp1(x, y, 4, 'pchip', 0);"
            " d = interp1(x, y, 4, 'linear', 'extrap'); e = interp1(x, y, 4);")
    assert np.isclose(g("a")[0, 0], 64) and np.isclose(g("b")[0, 0], _ws("v = pchip(0:3, (0:3).^3, 1.5);")("v")[0, 0])
    assert g("c")[0, 0] == 0 and np.isclose(g("d")[0, 0], 46) and np.isnan(g("e")[0, 0])


def test_interp2_linear_nearest_and_grid():
    g = _ws("[X, Y] = meshgrid(1:3, 1:2); Z = X + 10*Y; a = interp2(X, Y, Z, 2.5, 1.5); b = interp2(Z, 2.5, 1.5);"
            " c = interp2(X, Y, Z, 5, 1); d = interp2(X, Y, Z, 2.4, 1.6, 'nearest'); G = interp2(1:3, 1:2, Z, [1 2], [1; 2]);"
            " e = interp2(X, Y, Z, 9, 9, 'linear', -1);")
    assert np.isclose(g("a")[0, 0], 17.5) and np.isclose(g("b")[0, 0], 17.5) and np.isnan(g("c")[0, 0])
    assert g("d")[0, 0] == 22 and g("G").tolist() == [[11, 12], [21, 22]] and g("e")[0, 0] == -1


def test_polyder_polyint():
    g = _ws("a = polyder([1 2 3]); b = polyder([1 1], [1 -1]); [q, d] = polyder([1 0], [1 1]); c = polyint([3 2 1]);"
            " k = polyint([1 1], 2); z = polyder(5);")
    assert g("a").tolist() == [[2, 2]] and g("b").tolist() == [[2, 0]]
    assert g("q").tolist() == [[1]] and g("d").tolist() == [[1, 2, 1]]
    assert g("c").tolist() == [[1, 1, 1, 0]] and g("k").tolist() == [[0.5, 1, 2]] and g("z").tolist() == [[0]]


def test_poly_from_roots_and_matrix():
    g = _ws("a = poly([1 2]); b = poly([1 2; 3 4]); c = poly([]);")
    assert g("a").tolist() == [[1, -3, 2]] and np.allclose(g("b"), [[1, -5, -2]]) and g("c").tolist() == [[1]]
