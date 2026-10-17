"""Epic #537: handle graphics model."""

from __future__ import annotations

import os

import numpy as np
import pytest

pytest.importorskip("matplotlib")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]


def _run(code, s=None):
    s = s or Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer())


def test_plot_returns_line_handles_per_column():
    s = _run("h = plot([1 2; 3 4]); n = numel(h); t = get(h(1), 'Type');")
    assert _v(s, "n").item() == 2 and s.workspace.get("t").text == "line"


def test_plot_reuses_figure_and_hold_accumulates():
    s = _run("plot(1:3); plot(1:2); a = numel(get(gca, 'Children')); hold on; plot(1:4); b = numel(get(gca, 'Children')); n = numel(get(0, 'Children'));")
    assert _v(s, "a").item() == 1 and _v(s, "b").item() == 2 and _v(s, "n").item() == 1


def test_linespec_and_default_color_order():
    s = _run("p = plot(1:3, 'r--o'); c = get(p, 'Color'); ls = get(p, 'LineStyle'); mk = get(p, 'Marker'); hold on; q = plot(1:3); d = get(q, 'Color');")
    assert _v(s, "c").tolist() == [[1, 0, 0]] and s.workspace.get("ls").text == "--"
    assert s.workspace.get("mk").text == "o"
    assert np.allclose(_v(s, "d"), [[0, 0.4470, 0.7410]])


def test_set_get_validation():
    with pytest.raises(Exception, match="Unrecognized property"):
        _run("p = plot(1:3); set(p, 'Bogus', 1);")
    with pytest.raises(Exception, match="read-only"):
        _run("p = plot(1:3); set(p, 'Type', 'x');")
    with pytest.raises(Exception, match="RGB triplet"):
        _run("p = plot(1:3); set(p, 'Color', [2 0 0]);")
    with pytest.raises(Exception, match="Invalid or deleted"):
        _run("t = get(99, 'Type');")


def test_decorations_limits_grid():
    s = _run("plot(1:3); title('T'); xlabel('x'); grid on; axis([0 4 0 10]); xl = xlim; xlim([1 3]); x2 = get(gca, 'XLim'); m = xlim('mode'); t = get(get(gca, 'Title'), 'String'); g = get(gca, 'XGrid');")
    assert _v(s, "xl").tolist() == [[0, 4]] and _v(s, "x2").tolist() == [[1, 3]]
    assert s.workspace.get("m").text == "manual" and s.workspace.get("t").text == "T"
    assert s.workspace.get("g").text == "on"


def test_hold_off_replace_resets_axes():
    s = _run("plot(1:3); title('T'); plot(1:2); t = get(get(gca, 'Title'), 'String');")
    assert s.workspace.get("t").text == ""


def test_subplot_replaces_full_axes_and_reuses_slot():
    s = _run("plot(1:3); a = subplot(2, 1, 1); b = subplot(2, 1, 2); c = subplot(2, 1, 1); n = numel(get(gcf, 'Children')); same = isequal(a, c);")
    assert _v(s, "n").item() == 2 and _v(s, "same").item()
    with pytest.raises(Exception, match="Index exceeds"):
        _run("subplot(2, 2, 5);")


def test_figure_numbers_close_and_current():
    s = _run("f = figure; g = figure(7); n = get(g, 'Number'); figure(f); cur = isequal(gcf, f); close(g); alive = ishandle(g); close all; e = isempty(get(0, 'Children'));")
    assert _v(s, "n").item() == 7 and _v(s, "cur").item()
    assert not _v(s, "alive").item() and _v(s, "e").item()


def test_bar_scatter_histogram():
    s = _run("b = bar([3 1 2]); by = get(b, 'YData'); hold on; sc = scatter([1 2], [3 4]); sx = get(sc, 'XData'); h = histogram([1 2 2 3 3 3], 'BinEdges', [0.5 1.5 2.5 3.5]); hv = get(h, 'Values');")
    assert _v(s, "by").tolist() == [[3, 1, 2]] and _v(s, "sx").tolist() == [[1, 2]]
    assert _v(s, "hv").tolist() == [[1, 2, 3]]


def test_saveas_png_and_unsupported_fig(tmp_path):
    p = str(tmp_path / "out.png")
    _run(f"plot(1:3); saveas(gcf, '{p}');")
    assert os.path.getsize(p) > 0
    # OpenMATLAB-own .fig via saveas (Shaw 2026-10-17, #979)
    figp = tmp_path / "x.fig"
    _run(f"plot(1:3); saveas(gcf, '{figp}');")
    assert figp.is_file() and figp.stat().st_size > 0
    with pytest.raises(Exception, match="unsupported format"):
        _run(f"plot(1:3); saveas(gcf, '{tmp_path / 'x.xyz'}');")


def test_statement_calls_do_not_set_ans_and_delete_file_still_works(tmp_path):
    f = tmp_path / "z.txt"
    f.write_text("x")
    s = _run(f"plot(1:3)\ndelete('{f}');")
    assert "ans" not in s.workspace.names()
    assert not f.exists()
