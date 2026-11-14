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


def _caught(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def test_unimplemented_ode_options_error_before_integration():
    """A set, unimplemented option errors and does not call the ODE or bind outputs."""
    cases = [
        ("ode45", "odeset('Events', @(t, y) y)", "option 'Events'", "UnsupportedOption"),
        ("ode23", "odeset('Events', @(t, y) y)", "option 'Events'", "UnsupportedOption"),
        ("ode45", "odeset('eVeNtS', @(t, y) y)", "option 'Events'", "UnsupportedOption"),
        ("ode45", "odeset('Ev', @(t, y) y)", "option 'Events'", "UnsupportedOption"),
        ("ode45", "odeset('Mass', eye(2))", "option 'Mass'", "UnsupportedOption"),
        ("ode23", "odeset('Mass', @(t) 1)", "option 'Mass'", "UnsupportedOption"),
        ("ode45", "struct('mass', eye(2))", "option 'Mass'", "UnsupportedOption"),
        ("ode45", "odeset('RelTol', 1e-8, 'Jacobian', [0 -1; 1 0], 'Events', @(t, y) y)",
         "option 'Events'", "UnsupportedOption"),
        ("ode23", "odeset('NonNegative', 1)", "option 'NonNegative'", "UnsupportedOption"),
        ("ode45", "odeset('OutputFcn', @(t, y, flag) 0)", "option 'OutputFcn'", "UnsupportedOption"),
        ("ode45", "odeset('OutputSel', 1)", "option 'OutputSel'", "UnsupportedOption"),
        ("ode45", "odeset('NormControl', 'on')", "option 'NormControl'", "UnsupportedOption"),
        ("ode45", "odeset('NormControl', \"on\")", "option 'NormControl'", "UnsupportedOption"),
        ("ode45", "odeset('Stats', 'on')", "option 'Stats'", "UnsupportedOption"),
        ("ode45", "odeset('Jacobian', [0 -1; 1 0])", "option 'Jacobian'", "UnsupportedOption"),
        ("ode45", "odeset('JPattern', 1)", "option 'JPattern'", "UnsupportedOption"),
        ("ode45", "odeset('JConstant', 'on')", "option 'JConstant'", "UnsupportedOption"),
        ("ode45", "odeset('Vectorized', 'on')", "option 'Vectorized'", "UnsupportedOption"),
        ("ode45", "odeset('BDF', 'on')", "option 'BDF'", "UnsupportedOption"),
        ("ode45", "odeset('MaxOrder', 2)", "option 'MaxOrder'", "UnsupportedOption"),
        ("ode45", "odeset('MassSingular', 'yes')", "option 'MassSingular'", "UnsupportedOption"),
        ("ode45", "odeset('MassSingular', 'no')", "option 'MassSingular'", "UnsupportedOption"),
        ("ode45", "odeset('MStateDependence', 'none')", "option 'MStateDependence'", "UnsupportedOption"),
        ("ode45", "odeset('MvPattern', 1)", "option 'MvPattern'", "UnsupportedOption"),
        ("ode45", "odeset('InitialSlope', 0)", "option 'InitialSlope'", "UnsupportedOption"),
        ("ode45", "1", "structure created with odeset", "OptionsNotStructure"),
        ("ode23", "'Events'", "structure created with odeset", "OptionsNotStructure"),
    ]
    for solver, opt, fragment, kind in cases:
        code = (
            f"try, [t, y] = {solver}(@(t, y) error('integrated'), [0 1], 1, {opt}); "
            "ok = 1; id = ''; msg = ''; catch err, ok = 0; id = err.identifier; msg = err.message; end; "
            "kept = exist('t', 'var') + exist('y', 'var');"
        )
        s = _caught(code)
        assert _n(s.workspace.get("ok"))[0, 0] == 0, opt
        assert s.workspace.get("id").text == f"OpenMATLAB:{solver}:{kind}", opt
        assert fragment in s.workspace.get("msg").text, opt
        assert "integrated" not in s.workspace.get("msg").text, opt
        assert _n(s.workspace.get("kept"))[0, 0] == 0, opt

    for solver, opt in (
        ("ode45", "odeset('Events', @(t, y) y)"),
        ("ode23", "odeset('Mass', eye(2))"),
    ):
        code = (
            f"try, sol = {solver}(@(t, y) error('integrated'), [0 1], 1, {opt}); "
            "ok = 1; id = ''; msg = ''; catch err, ok = 0; id = err.identifier; msg = err.message; end; "
            "kept = exist('sol', 'var');"
        )
        s = _caught(code)
        assert _n(s.workspace.get("ok"))[0, 0] == 0
        assert s.workspace.get("id").text == f"OpenMATLAB:{solver}:UnsupportedOption"
        assert "integrated" not in s.workspace.get("msg").text
        assert _n(s.workspace.get("kept"))[0, 0] == 0


def test_supported_ode_options_still_integrate():
    g = _ws(
        "[t0, y0] = ode45(@(t, y) -y, [0 1], 1); "
        "[t1, y1] = ode45(@(t, y) -y, [0 1], 1, []); "
        "[t2, y2] = ode45(@(t, y) -y, [0 1], 1, odeset()); "
        "[t3, y3] = ode45(@(t, y) -y, [0 1], 1, struct()); "
        "o = odeset('Events', [], 'Mass', [], 'NormControl', \"off\", 'Stats', 'off', "
        "'BDF', 'off', 'Vectorized', 'off', 'JConstant', 'off'); "
        "try, odeset('MinStep', 1e-6); mid = ''; catch err, mid = err.identifier; end; "
        "[t4, y4] = ode45(@(t, y) -y, [0 1], 1, o); "
        "[u, z] = ode23(@(t, y) -y, [0 1], 1, odeset('Events', [], 'Mass', [])); "
        "[t5, y5] = ode45(@(t, y) -y, [0 1], 1, odeset('RelTol', 1e-6, 'AbsTol', 1e-9, "
        "'InitialStep', 1e-3, 'MaxStep', 0.2, 'Refine', 2)); "
        "h = odeset('Events', @(t, y) y); eh = odeget(h, 'Events'); "
        "c = odeset(h, 'Events', []); [t6, y6] = ode45(@(t, y) -y, [0 1], 1, c); "
        "p = ode45(@(t, y) -y, [0 1], 1, struct('RelTol', 1e-6)); "
        "k = p.solver; py = p.y(end);"
    )
    y0 = _n(g("y0"))
    for name in ("y1", "y2", "y3", "y4", "y6"):
        assert np.allclose(_n(g(name)), y0)
    for name in ("t1", "t2", "t3", "t4", "t6"):
        assert np.allclose(_n(g(name)), _n(g("t0")))
    assert abs(_n(g("z"))[-1, 0] - np.exp(-1)) < 1e-3
    t5, y5 = _n(g("t5")), _n(g("y5"))
    assert t5[0, 0] == 0 and t5[-1, 0] == 1
    assert abs(y5[-1, 0] - np.exp(-1)) < 1e-5
    assert g("eh").matlab_class() == "function_handle"
    assert g("k").text == "ode45"
    assert abs(_n(g("py"))[0, 0] - np.exp(-1)) < 1e-5
    assert g("mid").text == "MATLAB:odeset:InvalidPropName"


def _rejected(solver, setup):
    code = (
        f"{setup} try, [t, y] = {solver}(@(t, y) error('integrated'), [0 1], 1, o); "
        "ok = 1; id = ''; msg = ''; catch err, ok = 0; id = err.identifier; msg = err.message; end; "
        "kept = exist('t', 'var') + exist('y', 'var');"
    )
    s = _caught(code)
    assert _n(s.workspace.get("ok"))[0, 0] == 0, (solver, setup)
    assert "integrated" not in s.workspace.get("msg").text, (solver, setup)
    assert _n(s.workspace.get("kept"))[0, 0] == 0, (solver, setup)
    return s.workspace.get("id").text, s.workspace.get("msg").text


def test_case_alias_and_nonscalar_options_error_before_integration():
    """An empty canonical field must not hide another spelling, and only element 1 is not enough."""
    toggles = ("NormControl", "Stats", "BDF", "Vectorized", "JConstant")
    for solver in ("ode45", "ode23"):
        for opt in toggles:
            low = opt.lower()
            for setup in (
                f"o = odeset('{opt}', 'off'); o.{low} = 'on';",
                f"o = struct('{low}', 'on'); o.{opt} = 'off';",
            ):
                ident, msg = _rejected(solver, setup)
                assert ident == f"OpenMATLAB:{solver}:UnsupportedOption", setup
                assert f"option '{opt}'" in msg, setup
        for setup in (
            "o = odeset(); o.events = @(t, y) y;",
            "o = struct('events', @(t, y) y); o.Events = [];",
            "o = odeset(); o.mass = 1;",
            "o = struct('mass', 1); o.Mass = [];",
        ):
            ident, msg = _rejected(solver, setup)
            assert ident == f"OpenMATLAB:{solver}:UnsupportedOption", setup
            assert "option 'Events'" in msg or "option 'Mass'" in msg, setup
        for setup in (
            "o = odeset('Refine', 1); o.refine = 4;",
            "o = struct('refine', 4); o.Refine = 1;",
            "o = odeset('RelTol', 1e-6); o.reltol = 1e-2;",
            "o = struct('reltol', 1e-2); o.RelTol = 1e-6;",
        ):
            ident, msg = _rejected(solver, setup)
            assert ident == f"OpenMATLAB:{solver}:AmbiguousOption", setup
            assert "more than once" in msg, setup
        for setup in (
            "o = odeset(); o(2) = odeset('Mass', 1);",
            "o = odeset('Mass', 1); o(2) = odeset();",
            "o = odeset(); o(2) = odeset();",
        ):
            ident, msg = _rejected(solver, setup)
            assert ident == f"OpenMATLAB:{solver}:OptionsNotStructure", setup
            assert "scalar structure" in msg, setup
        code = (
            f"o = odeset(); o.events = @(t, y) y; "
            f"try, sol = {solver}(@(t, y) error('integrated'), [0 1], 1, o); "
            "ok = 1; id = ''; msg = ''; catch err, ok = 0; id = err.identifier; msg = err.message; end; "
            "kept = exist('sol', 'var');"
        )
        s = _caught(code)
        assert s.workspace.get("id").text == f"OpenMATLAB:{solver}:UnsupportedOption"
        assert "integrated" not in s.workspace.get("msg").text
        assert _n(s.workspace.get("kept"))[0, 0] == 0


def test_case_alias_of_applied_option_and_empty_struct_still_integrate():
    g = _ws(
        "[t0, y0] = ode45(@(t, y) -y, [0 1], 1); "
        "[tr, yr] = ode45(@(t, y) -y, [0 1], 1, odeset('Refine', 1)); "
        "a = odeset(); a.refine = 1; [t1, y1] = ode45(@(t, y) -y, [0 1], 1, a); "
        "b = struct('refine', 1); b.Refine = []; [t2, y2] = ode45(@(t, y) -y, [0 1], 1, b); "
        "[u0, z0] = ode23(@(t, y) -y, [0 1], 1); "
        "[um, zm] = ode23(@(t, y) -y, [0 1], 1, odeset('MaxStep', 0.05)); "
        "c = odeset(); c.maxstep = 0.05; [u1, z1] = ode23(@(t, y) -y, [0 1], 1, c); "
        "d = struct('maxstep', 0.05); d.MaxStep = []; [u2, z2] = ode23(@(t, y) -y, [0 1], 1, d); "
        "e = odeset(); e(:) = []; [t3, y3] = ode45(@(t, y) -y, [0 1], 1, e); "
        "f = odeset('Events', @(t, y) y); f(:) = []; [t4, y4] = ode45(@(t, y) -y, [0 1], 1, f); "
        "g = odeset(); g(:) = []; [u3, z3] = ode23(@(t, y) -y, [0 1], 1, g); "
        "h = odeset('NormControl', 'off'); h.normcontrol = 'off'; "
        "[t5, y5] = ode45(@(t, y) -y, [0 1], 1, h);"
    )
    bare_t, bare_y = _n(g("t0")), _n(g("y0"))
    explicit_t, explicit_y = _n(g("tr")), _n(g("yr"))
    assert explicit_t.shape != bare_t.shape
    assert np.allclose(_n(g("t1")), explicit_t) and np.allclose(_n(g("y1")), explicit_y)
    assert np.allclose(_n(g("t2")), explicit_t) and np.allclose(_n(g("y2")), explicit_y)
    step_t, step_y = _n(g("um")), _n(g("zm"))
    assert step_t.shape != _n(g("u0")).shape
    assert np.allclose(_n(g("u1")), step_t) and np.allclose(_n(g("z1")), step_y)
    assert np.allclose(_n(g("u2")), step_t) and np.allclose(_n(g("z2")), step_y)
    assert np.allclose(_n(g("t3")), bare_t) and np.allclose(_n(g("y3")), bare_y)
    assert np.allclose(_n(g("t4")), bare_t) and np.allclose(_n(g("y4")), bare_y)
    assert np.allclose(_n(g("u3")), _n(g("u0"))) and np.allclose(_n(g("z3")), _n(g("z0")))
    assert np.allclose(_n(g("t5")), bare_t) and np.allclose(_n(g("y5")), bare_y)


# RHS records a base-workspace side effect and then errors. Either effect means it ran.
_CHAIN_RHS = "@(t, y) eval('assignin(''base'',''saw'',1); error(''integrated'')')"


def _chain(setup, call):
    code = (
        "saw = 0; "
        f"{setup} "
        f"try, {call} "
        "ok = 1; id = ''; msg = ''; catch err, ok = 0; id = err.identifier; msg = err.message; end; "
        "kept = exist('t', 'var') + exist('y', 'var');"
    )
    s = _caught(code)
    return (
        _n(s.workspace.get("ok"))[0, 0],
        s.workspace.get("id").text,
        s.workspace.get("msg").text,
        _n(s.workspace.get("kept"))[0, 0],
        _n(s.workspace.get("saw"))[0, 0],
    )


def test_odeset_copy_preserves_the_option_entry_chain():
    """Copy, explicit override, and the solver are one chain. A set value is not dropped."""
    rhs = _CHAIN_RHS
    toggles = ("NormControl", "Stats", "BDF", "Vectorized", "JConstant")
    for opt in toggles:
        low = opt.lower()
        for setup in (
            f"o = struct('{low}', 'on'); o.{opt} = 'off';",
            f"o = struct('{opt}', 'off'); o.{low} = 'on';",
        ):
            for solver in ("ode45", "ode23"):
                ok, ident, msg, kept, saw = _chain(
                    setup, f"p = odeset(o); [t, y] = {solver}({rhs}, [0 1], 1, p);"
                )
                assert ok == 0 and kept == 0 and saw == 0, setup
                assert ident == "OpenMATLAB:odeset:AmbiguousOption", (setup, ident, msg)
                assert "more than once" in msg and f"option '{opt}'" in msg
                assert "integrated" not in msg

    for setup in (
        "o = odeset(); o(2) = odeset('Mass', 1);",
        "o = odeset('Mass', 1); o(2) = odeset();",
        "o = odeset(); o(2) = odeset();",
    ):
        for solver in ("ode45", "ode23"):
            ok, ident, msg, kept, saw = _chain(
                setup, f"p = odeset(o); [t, y] = {solver}({rhs}, [0 1], 1, p);"
            )
            assert ok == 0 and kept == 0 and saw == 0, setup
            assert ident == "OpenMATLAB:odeset:OptionsNotStructure", (setup, ident, msg)
            assert "scalar structure" in msg and "integrated" not in msg

    for solver, setup, fragment in (
        ("ode23", "o = odeset(); o.mass = 1;", "option 'Mass'"),
        ("ode45", "o = struct('events', @(t, y) y);", "option 'Events'"),
        ("ode23", "o = struct('mass', 1); o.Mass = 1;", "option 'Mass'"),
        ("ode45", "o = struct('normcontrol', 'on'); o.NormControl = 'ON';", "option 'NormControl'"),
    ):
        ok, ident, msg, kept, saw = _chain(
            setup, f"p = odeset(o); [t, y] = {solver}({rhs}, [0 1], 1, p);"
        )
        assert ok == 0 and kept == 0 and saw == 0, setup
        assert ident == f"OpenMATLAB:{solver}:UnsupportedOption", (setup, ident, msg)
        assert fragment in msg and "integrated" not in msg

    for setup in (
        "o = odeset('Events', @(t, y) y); o.events = @(t, y) 1;",
        "o = odeset('InitialStep', 0.01); o.initialstep = 0.02;",
        "o = struct('initialstep', 0.02); o.InitialStep = 0.01;",
    ):
        ok, ident, msg, kept, saw = _chain(setup, "p = odeset(o);")
        assert ok == 0 and kept == 0 and saw == 0, setup
        assert ident == "OpenMATLAB:odeset:AmbiguousOption", (setup, ident, msg)
        assert "integrated" not in msg

    # An explicit pair wins, including a pair that clears. A later structure's [] does not.
    g = _ws(
        "[t0, y0] = ode45(@(t, y) -y, [0 1], 1); "
        "o = odeset('Events', @(t, y) y); o.events = @(t, y) 1; "
        "c = odeset(o, 'Events', []); [t1, y1] = ode45(@(t, y) -y, [0 1], 1, c); "
        "n = struct('normcontrol', 'on'); n.NormControl = 'off'; "
        "d = odeset(n, 'NormControl', 'off'); [t2, y2] = ode45(@(t, y) -y, [0 1], 1, d); "
        "z = odeset('Mass', 1); z(:) = []; p = odeset(z); "
        "[t3, y3] = ode45(@(t, y) -y, [0 1], 1, p); "
        "[u3, z3] = ode23(@(t, y) -y, [0 1], 1, p); "
        "q = odeset(z, 'RelTol', 1e-6); rq = odeget(q, 'RelTol'); "
        "[t4, y4] = ode45(@(t, y) -y, [0 1], 1, q); "
        "[t5, y5] = ode45(@(t, y) -y, [0 1], 1, odeset('RelTol', 1e-6)); "
        "a = odeset('Mass', 1); b = odeset(); "
        "try, [tm, ym] = ode23(@(t, y) error('integrated'), [0 1], 1, odeset(a, b)); "
        "mid = ''; mmsg = ''; catch err, mid = err.identifier; mmsg = err.message; end; "
        "e = odeset(a, 'Mass', []); [t6, y6] = ode23(@(t, y) -y, [0 1], 1, e); "
        "[u0, v0] = ode23(@(t, y) -y, [0 1], 1); "
        "s1 = odeset('RelTol', 1e-4); s2 = odeset('RelTol', 1e-8); "
        "rr = odeget(odeset(s1, s2), 'RelTol'); "
        "h = odeset(); h.initialstep = 0.25; hp = odeget(odeset(h), 'InitialStep'); "
        "[ti, yi] = ode45(@(t, y) -y, [0 1], 1, odeset(h)); "
        "[tj, yj] = ode45(@(t, y) -y, [0 1], 1, odeset('InitialStep', 0.25)); "
        "w = struct('normcontrol', 'off'); w.NormControl = 'Off'; "
        "[t7, y7] = ode45(@(t, y) -y, [0 1], 1, odeset(w)); "
        "r = struct('reltol', 1e-6); r.RelTol = []; rgot = odeget(odeset(r), 'RelTol'); "
        "rf = odeset(); rf.refine = 1; "
        "[t8, y8] = ode45(@(t, y) -y, [0 1], 1, odeset(rf)); "
        "[t9, y9] = ode45(@(t, y) -y, [0 1], 1, odeset('Refine', 1));"
    )
    bare_t, bare_y = _n(g("t0")), _n(g("y0"))
    for name in ("t1", "t2", "t3", "t7"):
        assert np.allclose(_n(g(name)), bare_t)
    for name in ("y1", "y2", "y3", "y7"):
        assert np.allclose(_n(g(name)), bare_y)
    assert np.allclose(_n(g("u3")), _n(g("u0"))) and np.allclose(_n(g("z3")), _n(g("v0")))
    assert _n(g("rq"))[0, 0] == 1e-6
    assert np.allclose(_n(g("t4")), _n(g("t5"))) and np.allclose(_n(g("y4")), _n(g("y5")))
    assert g("mid").text == "OpenMATLAB:ode23:UnsupportedOption"
    assert "option 'Mass'" in g("mmsg").text and "integrated" not in g("mmsg").text
    assert np.allclose(_n(g("t6")), _n(g("u0"))) and np.allclose(_n(g("y6")), _n(g("v0")))
    assert _n(g("rr"))[0, 0] == 1e-8
    assert _n(g("hp"))[0, 0] == 0.25
    assert np.allclose(_n(g("ti")), _n(g("tj"))) and np.allclose(_n(g("yi")), _n(g("yj")))
    assert _n(g("rgot"))[0, 0] == 1e-6
    assert _n(g("t8")).shape != bare_t.shape
    assert np.allclose(_n(g("t8")), _n(g("t9"))) and np.allclose(_n(g("y8")), _n(g("y9")))

    ok, ident, msg, kept, saw = _chain(
        "o = struct('normcontrol', 'on'); o.NormControl = 'off';",
        f"p = odeset(o, 'NormControl', 'on'); [t, y] = ode45({rhs}, [0 1], 1, p);",
    )
    assert ok == 0 and kept == 0 and saw == 0
    assert ident == "OpenMATLAB:ode45:UnsupportedOption"
    assert "option 'NormControl'" in msg and "integrated" not in msg


def test_initialstep_alias_is_checked_before_the_first_rhs():
    """Disagreeing InitialStep spellings error before the RHS side effect or its error."""
    rhs = _CHAIN_RHS
    for solver in ("ode45", "ode23"):
        for setup in (
            "o = odeset('InitialStep', 0.01); o.initialstep = 0.02;",
            "o = struct('initialstep', 0.02); o.InitialStep = 0.01;",
        ):
            ok, ident, msg, kept, saw = _chain(setup, f"[t, y] = {solver}({rhs}, [0 1], 1, o);")
            assert ok == 0 and kept == 0 and saw == 0, (solver, setup, ident, msg)
            assert ident == f"OpenMATLAB:{solver}:AmbiguousOption", (solver, setup, ident)
            assert "option 'InitialStep'" in msg and "more than once" in msg
            assert "integrated" not in msg
