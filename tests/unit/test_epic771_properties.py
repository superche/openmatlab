"""Epic #771 (M13 G-E4): remaining axes/ruler/figure/text properties (ticks, rulers, Units, fonts, interpreters)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs.axes_props import auto_ticks, to_mpl_text

pytestmark = [pytest.mark.unit]


def _run(code):
    s = ReplSession()
    s.run_line("figure('Visible','off'); " + code + " close all")
    return s.session.workspace


def _v(w, k):
    return np.asarray(w.get(k).backend_buffer())


def _t(w, k):
    return w.get(k).text


@pytest.mark.parametrize("lim,scale,want", [
    ([1, 10], None, list(range(1, 11))), ([0, 1], None, [round(0.1 * i, 12) for i in range(11)]),
    ([-1, 1], None, [-1, -0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1]), ([0, 100], None, list(range(0, 101, 10))),
    ([1, 1e5], "log", [1, 10, 100, 1e3, 1e4, 1e5]), ([1, 1], None, []),
])
def test_auto_ticks(lim, scale, want):
    np.testing.assert_allclose(auto_ticks(lim, scale), want)


def test_tick_modes_and_labels():
    w = _run("plot(1:10); ax = gca; t0 = ax.XTick; m0 = ax.XTickMode; ax.XTick = [1 5 10]; m1 = ax.XTickMode; "
             "l1 = ax.XTickLabel; xlim([0 20]); t1 = xticks; ax.XTickMode = 'auto'; t2 = xticks; "
             "ax.YTickLabel = [1 2 3]; yl = ax.YTickLabel; ym = ax.YTickLabelMode;")
    assert _v(w, "t0").tolist() == [list(range(1, 11))] and _t(w, "m0") == "auto" and _t(w, "m1") == "manual"
    assert [w.get("l1").get(j, 0).text for j in range(3)] == ["1", "5", "10"]  # Nx1 (Shaw #977)
    assert _v(w, "t1").tolist() == [[1, 5, 10]] and _v(w, "t2").tolist() == [list(range(0, 21, 2))]
    assert [w.get("yl").get(j, 0).text for j in range(3)] == ["1", "2", "3"] and _t(w, "ym") == "manual"  # Nx1


def test_log_tick_labels_and_tickangle():
    w = _run("semilogy(1:10, logspace(0, 3, 10)); yl = yticklabels; xtickangle(45); r = xtickangle; "
             "ax = gca; rm = ax.XTickLabelRotationMode;")
    assert [w.get("yl").get(j, 0).text for j in range(4)] == ["10^{0}", "10^{1}", "10^{2}", "10^{3}"]  # Nx1
    assert _v(w, "r").item() == 45 and _t(w, "rm") == "manual"


def test_rulers_proxy_axes_properties():
    w = _run("plot(1:10, (1:10).^2); ax = gca; r = ax.XAxis; c = class(r); r.Limits = [0 20]; xl = xlim; "
             "r.Direction = 'reverse'; d = ax.XDir; ax.YAxis.Exponent = 2; yl = ax.YTickLabel; "
             "ax.YAxis.TickLabelFormat = '%.1f'; yf = ax.YAxis.TickLabels; p = isequal(r.Parent, ax); "
             "lb = isequal(r.Label, ax.XLabel); ty = r.Type;")
    assert _t(w, "c") == "matlab.graphics.axis.decorator.NumericRuler" and _v(w, "xl").tolist() == [[0, 20]]
    assert _t(w, "d") == "reverse" and w.get("yl").get(10, 0).text == "1"  # Nx1
    assert w.get("yf").get(0, 0).text == "0.0" and _v(w, "p").item() and _v(w, "lb").item()  # (0,0) either shape
    assert _t(w, "ty") == "numericruler"


def test_yyaxis_ruler_array():
    w = _run("yyaxis left; plot(1:3); yyaxis right; plot([10 20 30]); ax = gca; y = ax.YAxis; n = numel(y); "
             "y(1).Limits = [-5 5]; yyaxis left; l = ylim; c2 = y(2).Color;")
    assert _v(w, "n").item() == 2 and _v(w, "l").tolist() == [[-5, 5]]
    np.testing.assert_allclose(_v(w, "c2"), [[0.85, 0.325, 0.098]])


def test_units_conversion():
    w = _run("ax = gca; ax.Units = 'pixels'; p = ax.Position; ax.Units = 'normalized'; q = ax.Position; "
             "f = gcf; f.Units = 'inches'; fi = f.Position; f.Units = 'normalized'; f.Position = [0 0 0.5 0.5]; "
             "f.Units = 'pixels'; fp = f.Position; ip = ax.InnerPosition;")
    np.testing.assert_allclose(_v(w, "p"), [[73.8, 47.2, 434, 342.3]])
    np.testing.assert_allclose(_v(w, "q"), [[0.13, 0.11, 0.775, 0.815]])
    np.testing.assert_allclose(_v(w, "fi"), [[99 / 96, 99 / 96, 560 / 96, 420 / 96]])
    np.testing.assert_allclose(_v(w, "fp"), [[1, 1, 960, 540]])
    np.testing.assert_allclose(_v(w, "ip"), [[0.13, 0.11, 0.775, 0.815]])


def test_text_units():
    w = _run("plot(1:10); t = text(5.5, 5.5, 'c'); t.Units = 'normalized'; n = t.Position; "
             "u = text(0.25, 0.75, 'u', 'Units', 'normalized'); up = u.Position; uu = u.Units; "
             "u.Units = 'data'; ud = u.Position;")
    np.testing.assert_allclose(_v(w, "n"), [[0.5, 0.5, 0]])
    np.testing.assert_allclose(_v(w, "up"), [[0.25, 0.75, 0]])
    assert _t(w, "uu") == "normalized"
    np.testing.assert_allclose(_v(w, "ud"), [[3.25, 7.75, 0]])


def test_label_font_multipliers_and_title_weight():
    w = _run("ax = gca; ax.FontSize = 14; xf = ax.XLabel.FontSize; tf = ax.Title.FontSize; tw = ax.Title.FontWeight; "
             "ax.YLabel.FontSize = 8; ax.FontSize = 20; yf = ax.YLabel.FontSize; xf2 = ax.XLabel.FontSize;")
    assert abs(_v(w, "xf").item() - 15.4) < 1e-9 and abs(_v(w, "tf").item() - 15.4) < 1e-9
    assert _t(w, "tw") == "bold" and _v(w, "yf").item() == 8 and abs(_v(w, "xf2").item() - 22) < 1e-9


def test_new_documented_properties():
    w = _run("h = plot(1:4); mi = h.MarkerIndices; ax = gca; ti = ax.TickLabelInterpreter; ga = ax.GridAlpha; "
             "f = gcf; cr = f.CloseRequestFcn; e = isempty(ax.Legend); lg = legend('a'); same = isequal(ax.Legend, lg); "
             "t = text(1, 1, 'x'); fu = t.FontUnits;")
    assert _v(w, "mi").tolist() == [[1, 2, 3, 4]] and _t(w, "ti") == "tex" and _v(w, "ga").item() == 0.15
    assert _t(w, "cr") == "closereq" and _v(w, "e").item() and _v(w, "same").item() and _t(w, "fu") == "points"


@pytest.mark.parametrize("code,ident", [
    ("ax = gca; ax.XTick = [3 1];", "MATLAB:hg:shaped_arrays:IncreasingVectorType"),
    ("ax = gca; ax.TickDir = 'sideways';", "MATLAB:datatypes:InvalidEnumValue"),
    ("ax = gca; ax.XAxis.Exponent = 1.5;", "MATLAB:hg:InvalidValue"),
    ("ax = gca; ax.Units = 'furlongs';", "MATLAB:datatypes:InvalidEnumValue"),
    ("ax = gca; ax.XAxis.Bogus = 1;", "MATLAB:class:InvalidProperty"),
    ("t = text(1, 1, 'a'); t.Interpreter = 'html';", "MATLAB:datatypes:InvalidEnumValue"),
    ("ax = gca; ax.Position = [0 0 1];", "MATLAB:hg:shaped_arrays:PositionType"),
])
def test_property_errors(code, ident):
    w = _run(f"try, {code} id = ''; catch e, id = e.identifier; end")
    assert _t(w, "id") == ident


@pytest.mark.parametrize("src,interp,want", [
    ("x^2", "tex", "x$^{2}$"), ("\\alpha_{1}", "tex", "$\\alpha_{1}$"), ("a$b", "tex", "a\\$b"),
    ("\\bf bold", "tex", "bold"), ("x^{", "tex", "x^{"), ("$x^2$", "latex", "$x^2$"),
    ("$\\frac{1$", "latex", "\\frac{1"), ("a_b $", "none", "a_b \\$"),
])
def test_interpreter_translation(src, interp, want):
    assert to_mpl_text(src, interp) == want


def test_rendering_never_fails(tmp_path):
    p = (tmp_path / "r.png").as_posix()
    w = _run("plot(1:10); title('\\alpha_{1}^2 $5 \\color{red} x_'); xlabel('a_b^c {'); "
             "ylabel('$\\frac{1$', 'Interpreter', 'latex'); text(2, 5, '\\int_0^\\infty \\nope x^{', 'Rotation', 30); "
             "set(gca, 'XTick', [1 5 10], 'XTickLabel', {'a', '\\beta', '$x$'}, 'TickLabelInterpreter', 'latex', "
             "'XTickLabelRotation', 45, 'TickDir', 'out', 'Box', 'off'); grid on; ax = gca; ax.XAxis.Color = [1 0 0]; "
             f"saveas(gcf, '{p}'); ok = isfile('{p}');")
    assert _v(w, "ok").item()
