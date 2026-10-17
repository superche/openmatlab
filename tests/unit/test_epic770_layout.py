"""Epic #770 (M13 G-E3): tiledlayout/nexttile, yyaxis, subplot geometry, nice auto limits, axis modes."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession

pytestmark = [pytest.mark.unit]


def _run(code):
    s = ReplSession()
    s.run_line("figure('Visible','off'); " + code + " close all")
    return s.session.workspace


def _v(w, k):
    return np.asarray(w.get(k).backend_buffer())


@pytest.mark.parametrize("data,want", [
    ("[0.3 9.7]", [0, 10]), ("1:3", [1, 3]), ("[1 5]", [1, 5]), ("[-0.04 0.17]", [-0.05, 0.2]),
    ("5*ones(1,3)", [4, 6]), ("[1e-12 2e-12]", [1e-12, 2e-12]),
])
def test_nice_auto_limits(data, want):
    np.testing.assert_allclose(_v(_run(f"plot({data}); yl = ylim;"), "yl"), [want])


def test_log_auto_limits_are_whole_decades():
    np.testing.assert_allclose(_v(_run("semilogy([2 300]); yl = ylim;"), "yl"), [[1, 1000]])


def test_tiledlayout_nexttile_tiles_and_spans():
    w = _run("t = tiledlayout(2, 2); a = nexttile; b = nexttile([1 2]); c = class(t); p = class(a.Parent);"
             " n = numel(t.Children); k = b.Layout.Tile; s = b.Layout.TileSpan; g = t.GridSize;"
             " a2 = nexttile(1); same = isequal(a, a2); f = numel(get(gcf, 'Children'));"
             " try, nexttile([2 2]); e = ''; catch err, e = err.identifier; end")
    assert w.get("c").text == "matlab.graphics.layout.TiledChartLayout"
    assert w.get("p").text == "matlab.graphics.layout.TiledChartLayout"
    assert _v(w, "n").item() == 2 and _v(w, "k").item() == 3 and _v(w, "s").tolist() == [[1, 2]]
    assert _v(w, "g").tolist() == [[2, 2]] and bool(_v(w, "same").item()) and _v(w, "f").item() == 1
    assert w.get("e").text == "MATLAB:tiledlayout:NoEmptyTiles"


def test_flow_layout_grows_and_spacing_options():
    w = _run("t = tiledlayout('flow'); for k = 1:5, nexttile; plot(1:k); end; g = t.GridSize;"
             " u = tiledlayout(1, 2, 'TileSpacing', 'compact', 'Padding', 'tight'); sp = u.TileSpacing;")
    assert _v(w, "g").tolist() == [[2, 3]] and w.get("sp").text == "compact"


def test_yyaxis_sides_scale_and_replace_independently():
    w = _run("ax = gca; plot(1:10); yyaxis right; plot([0 50]); r = ylim; loc = ax.YAxisLocation;"
             " yyaxis left; l = ylim; plot(3:4); l2 = ylim; n = numel(ax.Children); saveas(gcf, [tempname '.png']);")
    np.testing.assert_allclose(_v(w, "r"), [[0, 50]])
    np.testing.assert_allclose(_v(w, "l"), [[1, 10]])
    np.testing.assert_allclose(_v(w, "l2"), [[3, 4]])
    assert w.get("loc").text == "right" and _v(w, "n").item() == 2


def test_subplot_geometry_overlap_replace_and_position_form():
    w = _run("a = subplot(2, 2, 1); pa = a.Position; b = subplot(2, 2, [3 4]); pb = b.Position;"
             " subplot(2, 1, 1); n = numel(get(gcf, 'Children')); s = subplot('Position', [0.1 0.1 0.2 0.2]);"
             " ps = s.Position;")
    pa, pb = _v(w, "pa")[0], _v(w, "pb")[0]
    assert pa[0] == pytest.approx(0.13) and pa[1] > 0.5 and pa[2] < 0.4
    assert pb[0] == pytest.approx(0.13) and pb[1] == pytest.approx(0.11) and pb[2] == pytest.approx(0.775)
    assert _v(w, "n").item() == 2  # subplot(2,1,1) replaced the overlapping (2,2,1) only
    np.testing.assert_allclose(_v(w, "ps"), [[0.1, 0.1, 0.2, 0.2]])


def test_axis_modes_set_documented_properties():
    w = _run("plot(1:3); axis equal; d = get(gca, 'DataAspectRatioMode'); axis square;"
             " pb = get(gca, 'PlotBoxAspectRatioMode'); axis ij; y1 = get(gca, 'YDir'); axis xy; y2 = get(gca, 'YDir');"
             " axis normal; d2 = get(gca, 'DataAspectRatioMode'); g = isgraphics(gca, 'axes'); h = isgraphics(gca, 'line');")
    assert w.get("d").text == "manual" and w.get("pb").text == "manual"
    assert w.get("y1").text == "reverse" and w.get("y2").text == "normal" and w.get("d2").text == "auto"
    assert bool(_v(w, "g").item()) and not bool(_v(w, "h").item())


def test_layout_errors_are_matlab_errors():
    w = _run("n = 0; try, tiledlayout(0, 2); catch e, n = n + strcmp(e.identifier, 'MATLAB:tiledlayout:InvalidGridSize'); end;"
             " try, yyaxis('up'); catch e, n = n + strcmp(e.identifier, 'MATLAB:yyaxis:InvalidSide'); end;"
             " try, tiledlayout(2, 2, 'TileSpacing', 'huge'); catch e, n = n + 1; end;")
    assert _v(w, "n").item() == 3
