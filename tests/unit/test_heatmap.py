"""heatmap matrix and table entry (M14 V-E4, Epic #997)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _session(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _n(v):
    return np.asarray(v.backend_buffer())


def _texts(value):
    return [item.text for row in value.rows for item in row]


def test_matrix_labels_limits_and_colorbar():
    s = _session(
        "h = heatmap({'s1','s2'}, {'r1','r2','r3'}, [1 2; 3 4; 5 6], 'ColorLimits', [-1 2]);"
        " cls = class(h); vis = h.ColorbarVisible; cd = h.ColorData; clim = h.ColorLimits;"
        " xl = h.XDisplayLabels; yl = h.YDisplayLabels;"
    )
    assert s.workspace.get("cls").text == "matlab.graphics.chart.HeatmapChart"
    assert s.workspace.get("vis").text == "on"
    assert np.allclose(_n(s.workspace.get("cd")), [[1, 2], [3, 4], [5, 6]])
    assert np.allclose(_n(s.workspace.get("clim")).reshape(-1), [-1, 2])
    assert _texts(s.workspace.get("xl")) == ["s1", "s2"]
    assert _texts(s.workspace.get("yl")) == ["r1", "r2", "r3"]
    fig = s.graphics.last_figure
    heat = [ax for ax in fig.axes if ax.images and np.allclose(np.asarray(ax.images[0].get_array(), float),
                                                               [[1, 2], [3, 4], [5, 6]])]
    assert len(heat) == 1
    ax = heat[0]
    assert [t.get_text() for t in ax.get_xticklabels()] == ["s1", "s2"]
    assert [t.get_text() for t in ax.get_yticklabels()] == ["r1", "r2", "r3"]
    im = ax.images[0]
    assert im.colorbar is not None
    assert im.norm.vmin == -1 and im.norm.vmax == 2


def test_wide_matrix_rotates_tick_labels_and_can_hide_the_colorbar():
    s = _session(
        "heatmap(reshape(1:16, 2, 8)); figure; off = heatmap(magic(3), 'ColorbarVisible', 'off'); v = off.ColorbarVisible;"
    )
    figs = [f for f in s.graphics._figures if f is not None]
    wide = [ax for ax in figs[0].axes if ax.images and np.asarray(ax.images[0].get_array()).shape == (2, 8)]
    assert wide and wide[0].get_xticklabels()[0].get_rotation() == 90
    assert wide[0].images[0].colorbar is not None
    plain = [ax for ax in figs[1].axes if ax.images and np.asarray(ax.images[0].get_array()).shape == (3, 3)]
    assert plain and plain[0].images[0].colorbar is None
    assert s.workspace.get("v").text == "off"


def test_table_count_and_mean_leave_a_missing_cell():
    # x columns a, b; y rows u, v. b/v never occurs. Expected grids are literals.
    s = _session(
        "x = {'a';'b';'a'}; y = {'u';'u';'v'}; c = [4;6;8]; T = table(x, y, c);"
        " hc = heatmap(T, 'x', 'y'); cc = hc.ColorData; xl = hc.XDisplayLabels; yl = hc.YDisplayLabels;"
        " figure; hm = heatmap(T, 'x', 'y', 'ColorVariable', 'c'); cm = hm.ColorData;"
    )
    assert np.allclose(_n(s.workspace.get("cc")), [[1, 1], [1, 0]])
    got = _n(s.workspace.get("cm"))
    assert np.allclose(got[0], [4, 6])
    assert got[1, 0] == 8 and np.isnan(got[1, 1])
    assert _texts(s.workspace.get("xl")) == ["a", "b"]
    assert _texts(s.workspace.get("yl")) == ["u", "v"]


def test_table_mean_averages_a_repeated_pair():
    s = _session(
        "x = {'a';'a';'b'}; y = {'u';'u';'u'}; c = [1;3;5]; T = table(x, y, c);"
        " h = heatmap(T, 'x', 'y', 'ColorVariable', 'c', 'ColorMethod', 'mean'); cd = h.ColorData;"
    )
    assert np.allclose(_n(s.workspace.get("cd")), [[2, 5]])


def test_heatmap_stays_on_the_current_tile():
    s = _session("figure; tiledlayout(1, 2); nexttile; plot(1:3); nexttile; heatmap([1 2; 3 4]);")
    figs = [f for f in s.graphics._figures if f is not None]
    assert len(figs) == 1
    images = [ax for ax in figs[0].axes if ax.images and np.allclose(np.asarray(ax.images[0].get_array(), float)[:2, :2],
                                                                    [[1, 2], [3, 4]])]
    assert len(images) == 1
    assert any(len(ax.lines) == 1 for ax in figs[0].axes)


def test_rejected_calls():
    g = _session(
        "try, heatmap(); m = ''; catch err, m = err.identifier; end;"
        " try, heatmap(rand(2, 2, 2)); m2 = ''; catch err, m2 = err.identifier; end;"
        " try, heatmap({'a','b'}, {'c'}, magic(2)); m3 = ''; catch err, m3 = err.identifier; end;"
        " try, heatmap(magic(2), 'ColorLimits', [1 -1]); m4 = ''; catch err, m4 = err.identifier; end;"
        " try, heatmap(magic(2), 'ColorMethod', 'mean'); m5 = ''; catch err, m5 = err.identifier; end;"
        " try, T = table((1:2)', (3:4)', 'VariableNames', {'x','y'}); heatmap(T, 'x', 'y', 'ColorMethod', 'median');"
        " m6 = ''; catch err, m6 = err.identifier; end;"
        " try, heatmap(magic(2), 'NotAProp', 1); m7 = ''; catch err, m7 = err.identifier; end;"
    )
    assert g.workspace.get("m").text == "MATLAB:narginchk:notEnoughInputs"
    assert g.workspace.get("m2").text == "OpenMATLAB:heatmap:ColorData"
    assert g.workspace.get("m3").text == "OpenMATLAB:heatmap:SizeMismatch"
    assert g.workspace.get("m4").text == "OpenMATLAB:heatmap:ColorLimits"
    assert g.workspace.get("m5").text == "OpenMATLAB:heatmap:TableVariable"
    assert g.workspace.get("m6").text == "OpenMATLAB:heatmap:ColorMethod"
    assert g.workspace.get("m7").text == "MATLAB:class:InvalidProperty"
