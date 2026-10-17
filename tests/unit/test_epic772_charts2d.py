"""Epic #772 (M13 G-E5): 2-D chart breadth and annotations."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("matplotlib")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line("figure('Visible','off'); " + code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer())


def _t(s, n):
    return s.workspace.get(n).text


@pytest.mark.parametrize("call,typ,cls", [
    ("errorbar(1:3, [2 3 4], [0.1 0.2 0.3])", "errorbar", "matlab.graphics.chart.primitive.ErrorBar"),
    ("area(1:3, [1 2 3])", "area", "matlab.graphics.chart.primitive.Area"),
    ("stairs(1:3)", "stair", "matlab.graphics.chart.primitive.Stair"),
    ("stem(1:3)", "stem", "matlab.graphics.chart.primitive.Stem"),
    ("patch([0 1 1], [0 0 1], 'r')", "patch", "matlab.graphics.primitive.Patch"),
    ("fill([0 1 1], [0 0 1], 'g')", "patch", "matlab.graphics.primitive.Patch"),
    ("rectangle('Position', [0 0 2 1], 'Curvature', [1 1])", "rectangle", "matlab.graphics.primitive.Rectangle"),
    ("line([0 1], [0 1])", "line", "matlab.graphics.chart.primitive.Line"),
    ("imagesc(magic(4))", "image", "matlab.graphics.primitive.Image"),
    ("pcolor(magic(4))", "surface", "matlab.graphics.primitive.Surface"),
    ("quiver(1:3, 1:3, [1 1 1], [0 1 0])", "quiver", "matlab.graphics.chart.primitive.Quiver"),
    ("annotation('arrow', [0.1 0.2], [0.1 0.2])", "arrowshape", "matlab.graphics.shape.Arrow"),
    ("annotation('textbox', [0.1 0.1 0.2 0.2], 'String', 'hi')", "textboxshape", "matlab.graphics.shape.TextBox"),
    ("colorbar", "colorbar", "matlab.graphics.illustration.ColorBar"),
])
def test_chart_types_and_classes(call, typ, cls):
    s = _run(f"h = {call}; t = h.Type; c = class(h);")
    assert _t(s, "t") == typ and _t(s, "c") == cls


def test_pie_bar_matrix_and_hist_counts():
    s = _run("p = pie([1 2 3]); n = numel(p); b = bar([1 2; 3 4], 'stacked'); nb = numel(b); "
             "bh = barh([1 2 3]); hz = bh.Horizontal; [c, x] = hist([1 2 2 3 3 3], 3);")
    assert _v(s, "n").item() == 6 and _v(s, "nb").item() == 2 and _t(s, "hz") == "on"
    assert _v(s, "c").tolist() == [[1, 2, 3]] and np.allclose(_v(s, "x"), [[4 / 3, 2, 8 / 3]])


def test_errorbar_deltas_and_limits():
    s = _run("e = errorbar(1:3, [2 3 4], [1 1 1]); d = e.YPositiveDelta; yl = ylim;")
    assert _v(s, "d").tolist() == [[1, 1, 1]] and _v(s, "yl").tolist() == [[1, 5]]


def test_log_scales_and_documented_properties():
    s = _run("loglog(1:10, 1:10); xs = get(gca, 'XScale'); set(gca, 'XTick', [1 10], 'XTickLabel', {'a','b'}, "
             "'XDir', 'reverse'); xt = get(gca, 'XTick'); xl = get(gca, 'XTickLabel'); xd = get(gca, 'XDir'); "
             "set(gcf, 'Units', 'normalized'); u = get(gcf, 'Units'); r = get(gca, 'YDir');")
    assert _t(s, "xs") == "log" and _v(s, "xt").tolist() == [[1, 10]] and _t(s, "xd") == "reverse"
    assert _t(s, "u") == "normalized" and _t(s, "r") == "normal"
    assert s.workspace.get("xl").get(1, 0).text == "b"  # Nx1 (Shaw #977)


def test_replace_plot_resets_axes_scale():
    s = _run("semilogy(1:3, [1 10 100]); plot(1:3); y = get(gca, 'YScale');")
    assert _t(s, "y") == "linear"


def test_text_3d_and_interpreter():
    s = _run("t = text(1, 2, 3, 'x^2', 'Interpreter', 'none'); p = t.Position; i = t.Interpreter; "
             "tt = text([1 2], [1 2], 'a'); n = numel(tt);")
    assert _v(s, "p").tolist() == [[1, 2, 3]] and _t(s, "i") == "none" and _v(s, "n").item() == 2


def test_colormaps_are_clean_room_tables():
    s = _run("g = gray(3); j = jet(64); h = hot(4); colormap(jet); m = colormap; caxis([0 10]); c = caxis;")
    assert _v(s, "g").tolist() == [[0, 0, 0], [0.5, 0.5, 0.5], [1, 1, 1]]
    j = _v(s, "j")
    assert j.shape == (64, 3) and j.min() >= 0 and j.max() <= 1
    # MATLAB default colormap length is 256 (Shaw 2026-10-17, #866)
    assert _v(s, "m").shape == (256, 3) and _v(s, "c").tolist() == [[0, 10]]


def test_axes_reparent_and_userdata():
    s = _run("a1 = gca; a2 = axes('Position', [0.1 0.1 0.3 0.3]); l = plot(a1, 1:3); set(l, 'Parent', a2); "
             "ok = isequal(l.Parent, a2); set(l, 'UserData', struct('k', 1)); u = get(l, 'UserData'); k = u.k;")
    assert _v(s, "ok").item() and _v(s, "k").item() == 1


@pytest.mark.parametrize("bad,msg", [
    ("annotation('blob')", "annotation: type"),
    ("pie([-1 2])", "nonnegative"),
    ("colormap('nosuchmap')", "unknown colormap"),
    ("colormap([2 0 0])", "m-by-3"),
    ("caxis([3 1])", "increasing"),
    ("errorbar(1:3)", "Not enough input"),
    ("bar(1:3, 1:2)", "same length"),
])
def test_errors_are_matlab_errors(bad, msg):
    with pytest.raises(Exception, match=msg):
        _run(bad)


def test_all_charts_render_and_save(tmp_path):
    out = tmp_path / "f.png"
    _run("subplot(2,2,1); errorbar(1:3,[1 2 3],[1 1 1]); hold on; stem(1:3); stairs(1:3); area(1:3); "
         "subplot(2,2,2); imagesc(magic(4)); colorbar; subplot(2,2,3); contourf(peaks(10)); "
         "subplot(2,2,4); pie([1 2]); annotation('textbox',[0.1 0.1 0.1 0.1]); "
         f"saveas(gcf, '{out}');")
    assert out.exists() and out.stat().st_size > 1000
