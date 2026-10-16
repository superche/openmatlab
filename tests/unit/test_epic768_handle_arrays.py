"""Epic #768 (M13 G-E1): graphics handle arrays and class names."""

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


def test_class_names_are_full_matlab_names():
    s = _run("h = plot(1:3); a = class(h); b = class(gca); c = class(gcf); d = class(h(1:0));")
    assert _t(s, "a") == "matlab.graphics.chart.primitive.Line"
    assert _t(s, "b") == "matlab.graphics.axis.Axes" and _t(s, "c") == "matlab.ui.Figure"


def test_indexing_transpose_concat_keep_handles():
    s = _run("h = plot(1:3, [1:3; 2:4]'); a = class(h(2)); b = class(h'); c = class([h(1) h(2)]); "
             "m = class([gca; h]); e = class(h(end));")
    for n in "abce":
        assert _t(s, n) == "matlab.graphics.chart.primitive.Line"
    assert _t(s, "m") == "matlab.graphics.Graphics"


def test_element_property_write_and_cs_list_read():
    s = _run("h = plot(1:3, [1:3; 2:4]'); h(2).LineWidth = 3; w = [h.LineWidth]; h(1).XData(2) = 7; x = h(1).XData;")
    assert _v(s, "w").tolist() == [[0.5, 3.0]] and _v(s, "x").tolist() == [[1, 7, 3]]


def test_dot_assignment_on_array_requires_scalar():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("figure('Visible','off'); h = plot(1:3, [1:3; 2:4]');")
    with pytest.raises(Exception, match="Scalar object required"):
        r.run_line("h.LineWidth = 2;")


def test_isvalid_isgraphics_delete_elementwise():
    s = _run("h = plot(1:3, [1:3; 2:4; 3:5]'); delete(h(2)); v = isvalid(h); g = isgraphics(h); delete(h); w = isvalid(h);")
    assert _v(s, "v").ravel().tolist() == [True, False, True] and _v(s, "g").ravel().tolist() == [True, False, True]
    assert not _v(s, "w").any()


def test_double_is_numeric_and_isa():
    s = _run("h = plot(1:3); d = class(double(h)); a = isa(h, 'handle'); b = isa(h, 'matlab.graphics.Graphics'); "
             "c = isa(h, 'double'); n = isnumeric(h);")
    assert _t(s, "d") == "double" and _v(s, "a").item() and _v(s, "b").item()
    assert not _v(s, "c").item() and not _v(s, "n").item()


def test_deletion_growth_loops_arrayfun_keep_handles():
    s = _run("h = plot(1:3, [1:3; 2:4; 3:5]'); h(2) = []; a = class(h); h(3) = h(1); b = class(h); "
             "k = 0; for g = h', k = k + g.LineWidth; end; w = arrayfun(@(t) t.LineWidth, h); c = class(get(gca, 'Children'));")
    assert _t(s, "a") == _t(s, "b") == _t(s, "c") == "matlab.graphics.chart.primitive.Line"
    assert _v(s, "k").item() == 1.5 and _v(s, "w").ravel().tolist() == [0.5, 0.5, 0.5]


def test_gobjects_placeholders():
    s = _run("g = gobjects(2, 1); a = class(g); g(1) = plot(1:3); v = isgraphics(g); n = size(gobjects(0));")
    assert _t(s, "a") == "matlab.graphics.GraphicsPlaceholder"
    assert _v(s, "v").ravel().tolist() == [True, False] and _v(s, "n").tolist() == [[0, 0]]


def test_display_with_properties(capsys):
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("figure('Visible','off'); h = plot(1:3, [1:3; 2:4]'); disp(h(1)); disp(h); d = h(1); delete(d); disp(d)")
    out = capsys.readouterr().out
    assert "Line with properties:" in out and "LineWidth: 0.5" in out
    assert "2×1 Line array:" in out and "handle to deleted Line" in out
