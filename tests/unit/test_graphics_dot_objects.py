"""O-E6 (#623): graphics handles on the class model (h.Prop get/set, isvalid, isobject) and datetime dot access."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture
def run():
    s = Session.create_default()
    r = ReplSession(s)

    def go(code):
        r.run_line(code)
        return lambda n: s.workspace.get(n)

    return go


def _n(v):
    return np.asarray(v.backend_buffer()).tolist()


def test_dot_get_and_set_on_line_and_axes(run):
    g = run("f = figure('Visible','off'); h = plot(1:3); h.LineWidth = 3; a = get(h,'LineWidth'); b = h.LineWidth;"
            " ax = gca; ax.XLim = [0 5]; l = get(ax,'XLim'); x2 = ax.XLim(2); t = h.Type; close(f);")
    assert _n(g("a")) == [[3.0]] and _n(g("b")) == [[3.0]] and _n(g("l")) == [[0.0, 5.0]]
    assert _n(g("x2")) == [[5.0]] and g("t").text == "line"


def test_handle_semantics_and_validity(run):
    g = run("f = figure('Visible','off'); h = plot(1:3); k = h; k.LineWidth = 5; w = h.LineWidth;"
            " o = isobject(h); v1 = isvalid(h); close(f); v2 = isvalid(h); n = h + 0;")
    assert _n(g("w")) == [[5.0]] and _n(g("o")) == [[True]]
    assert _n(g("v1")) == [[True]] and _n(g("v2")) == [[False]]
    assert g("n").matlab_class() == "double"


def test_errors_are_matlab_style(run):
    g = run("f = figure('Visible','off'); h = plot(1:3);"
            " try, h.Type = 'x'; m1 = ''; catch e, m1 = e.message; end;"
            " close(f); try, h.LineWidth; m2 = ''; catch e, m2 = e.message; end")
    assert "read-only" in g("m1").text and g("m2").text == "Invalid or deleted object."


def test_datetime_components(run):
    g = run("dt = datetime(2020, 5, 6); y = [dt.Year dt.Month dt.Day];")
    assert _n(g("y")) == [[2020.0, 5.0, 6.0]]
