"""Epic #774 (M13 G-E7, G09 second half): docked figures and focus in the Workbench; Default<Type><Prop>."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.unit]


def _run(code):
    s = ReplSession()
    s.run_line(code + " close all")
    return s.session.workspace


def _v(w, k):
    return np.asarray(w.get(k).backend_buffer())


def _t(w, k):
    return w.get(k).text


def test_docked_figures_and_focus(tmp_path):
    pytest.importorskip("matplotlib")
    wb = Workbench.create(cwd=tmp_path)
    wb.eval("figure('WindowStyle','docked'); figure; plot(1:3);")
    figs = wb.figures.list()
    assert [f.number for f in figs] == [1, 2] and [f.docked for f in figs] == [True, False]
    assert [f.number for f in wb.figures.docked()] == [1] and wb.figures.focused() == 2
    wb.figures.focus(1.0)
    assert wb.figures.focused() == 1
    assert wb.eval("disp(get(gcf, 'Number'))").strip() == "1"
    wb.figures.set_docked(2.0)
    assert len(wb.figures.docked()) == 2
    wb.eval("figure(7);")
    assert wb.figures.focused() == 7
    wb.figures.close()
    assert wb.figures.list() == [] and wb.figures.focused() is None


def test_default_window_style_docks_new_figures(tmp_path):
    pytest.importorskip("matplotlib")
    wb = Workbench.create(cwd=tmp_path)
    wb.eval("set(groot, 'DefaultFigureWindowStyle', 'docked'); figure; plot(1:2);")
    assert [f.docked for f in wb.figures.list()] == [True]
    wb.eval("set(groot, 'DefaultFigureWindowStyle', 'normal'); figure;")
    assert [f.docked for f in wb.figures.list()] == [True, False]


def test_defaults_apply_to_new_objects():
    w = _run("set(groot, 'defaultLineLineWidth', 2); set(0, 'DefaultAxesFontSize', 14); f = figure('Visible','off'); "
             "h = plot(1:3, 'r:'); lw = h.LineWidth; ls = h.LineStyle; c = h.Color; fs = get(gca, 'FontSize'); "
             "xf = get(get(gca, 'XLabel'), 'FontSize'); g = get(groot, 'DefaultLineLineWidth'); "
             "ms = get(groot, 'DefaultLineMarkerSize'); s = get(groot, 'default'); n = numel(fieldnames(s)); "
             "set(groot, 'DefaultLineLineWidth', 'remove'); h2 = plot(1:2); lw2 = h2.LineWidth; "
             "set(groot, 'DefaultAxesFontSize', 'remove');")
    assert _v(w, "lw").item() == 2 and _t(w, "ls") == ":" and _v(w, "c").tolist() == [[1, 0, 0]]
    assert _v(w, "fs").item() == 14 and abs(_v(w, "xf").item() - 15.4) < 1e-9 and _v(w, "g").item() == 2
    assert _v(w, "ms").item() == 6 and _v(w, "n").item() == 2 and _v(w, "lw2").item() == 0.5


def test_nearest_ancestor_default_wins_and_labels_ignore_text_defaults():
    w = _run("set(groot, 'DefaultLineColor', [0 0 1]); f = figure('Visible','off'); set(f, 'DefaultLineColor', [1 0 0]); "
             "l = line([0 1], [0 1]); c = l.Color; set(groot, 'DefaultTextFontSize', 20); t = text(0, 0, 'x'); "
             "tf = t.FontSize; title('T'); ttf = get(get(gca, 'Title'), 'FontSize'); "
             "g = figure('Visible','off'); l2 = line([0 1], [0 1]); c2 = l2.Color; "
             "set(groot, 'DefaultLineColor', 'remove'); set(groot, 'DefaultTextFontSize', 'remove');")
    assert _v(w, "c").tolist() == [[1, 0, 0]] and _v(w, "c2").tolist() == [[0, 0, 1]]
    assert _v(w, "tf").item() == 20 and abs(_v(w, "ttf").item() - 11) < 1e-9


@pytest.mark.parametrize("code,ident", [
    ("set(groot, 'DefaultLineBogus', 1)", "MATLAB:hg:InvalidDefaultProperty"),
    ("set(groot, 'DefaultWidgetColor', 1)", "MATLAB:hg:InvalidDefaultProperty"),
    ("set(groot, 'DefaultLineLineWidth', -1)", "MATLAB:hg:InvalidValue"),
    ("get(groot, 'DefaultAxesNope')", "MATLAB:hg:InvalidDefaultProperty"),
])
def test_default_errors(code, ident):
    w = _run(f"try, {code}; id = ''; catch e, id = e.identifier; end;")
    assert _t(w, "id") == ident
