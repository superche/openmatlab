"""ODE solvers, quadrature, optimisation with options (M3-E3, Epic #627)."""

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


def test_ode45_ode23_accuracy_shapes_and_refine():
    g = _ws("[t, y] = ode45(@(t, y) -2*y, [0 1], 3); [u, z] = ode23(@(t, y) -2*y, [0 1], 3);"
            " [tv, yv] = ode45(@(t, y) -2*y, 0:0.25:1, 3); [tb, yb] = ode45(@(t, y) -y, [1 0], exp(-1));")
    t, y = _n(g("t")), _n(g("y"))
    assert t.shape[1] == 1 and t[0, 0] == 0 and t[-1, 0] == 1 and (t.shape[0] - 1) % 4 == 0
    assert abs(y[-1, 0] - 3 * np.exp(-2)) < 1e-3 and abs(_n(g("z"))[-1, 0] - 3 * np.exp(-2)) < 1e-3
    assert _n(g("tv")).reshape(-1).tolist() == [0, 0.25, 0.5, 0.75, 1]
    assert np.allclose(_n(g("yv")).reshape(-1), 3 * np.exp(-2 * np.arange(0, 1.01, 0.25)), atol=1e-3)
    assert abs(_n(g("yb"))[-1, 0] - 1) < 1e-3


def test_ode_system_with_odeset_tolerances():
    g = _ws("o = odeset('RelTol', 1e-9, 'abstol', 1e-12); [t, y] = ode45(@(t, y) [y(2); -y(1)], [0 2*pi], [1; 0], o);"
            " r = odeget(o, 'RelTol'); m = odeget(o, 'MaxStep', 7); s = ode45(@(t, y) -y, [0 1], 1); k = s.solver;")
    y = _n(g("y"))
    assert y.shape[1] == 2 and abs(y[-1, 0] - 1) < 1e-7 and abs(y[-1, 1]) < 1e-7
    assert _n(g("r"))[0, 0] == 1e-9 and _n(g("m"))[0, 0] == 7 and g("k").text == "ode45"


def test_integral_options_integral2_quad():
    g = _ws("a = integral(@(x) [sin(x) cos(x)], 0, pi, 'ArrayValued', true); b = integral2(@(x, y) x + y, 0, 1, 0, @(x) x);"
            " c = quad(@(x) 1 ./ x, 1, exp(1)); d = integral(@(x) 1 ./ (1 + x.^2), 0, Inf, 'RelTol', 1e-10);"
            " e = integral2(@(x, y) ones(size(x)), -1, 1, -1, 1);")
    assert np.allclose(_n(g("a")), [[2, 0]], atol=1e-8) and abs(_n(g("b"))[0, 0] - 0.5) < 1e-8
    assert abs(_n(g("c"))[0, 0] - 1) < 1e-6 and abs(_n(g("d"))[0, 0] - np.pi / 2) < 1e-8
    assert abs(_n(g("e"))[0, 0] - 4) < 1e-8


def test_fminbnd_and_optimset():
    g = _ws("[x, f, flag] = fminbnd(@(x) x.^2 - 4*x, -10, 10); o = optimset('tolx', 1e-10); x2 = fminbnd(@(x) (x - 1/3).^2, 0, 1, o);"
            " o2 = optimset(o, 'Display', 'iter'); t = optimget(o2, 'TolX'); d = o2.Display;"
            " try, optimset('Bogus', 1); e = ''; catch err, e = err.identifier; end")
    assert abs(_n(g("x"))[0, 0] - 2) < 1e-4 and abs(_n(g("f"))[0, 0] + 4) < 1e-8 and _n(g("flag"))[0, 0] == 1
    assert abs(_n(g("x2"))[0, 0] - 1 / 3) < 1e-8 and _n(g("t"))[0, 0] == 1e-10 and g("d").text == "iter"
    assert g("e").text == "MATLAB:optimset:InvalidPropName"


def test_fminsearch_honours_tolerances():
    g = _ws("p = fminsearch(@(p) (p(1) - 3)^2 + (p(2) - 1)^2, [0 0], optimset('TolX', 1e-10, 'TolFun', 1e-10));")
    assert np.max(np.abs(_n(g("p")) - [[3, 1]])) < 1e-6
