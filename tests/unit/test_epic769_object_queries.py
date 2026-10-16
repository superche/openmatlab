"""Epic #769 (M13 G-E2): findobj / findall / allchild / ancestor / groot."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("matplotlib")

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy, pytest.mark.needs_matplotlib]

SETUP = ("f = figure('Visible','off'); ax = axes(f); hold(ax, 'on'); l1 = plot(ax, 1:3, 'Tag', 'a'); "
         "l2 = plot(ax, 3:-1:1, 'Tag', 'b', 'Color', 'r'); ")


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(SETUP + code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer())


def test_findobj_order_and_predicates():
    s = _run("h = findobj(f, 'Type', 'line'); o = isequal(h, [l2; l1]); n = numel(findobj(f)); "
             "x = numel(findobj(f, 'Tag', 'a', '-or', 'Tag', 'b')); r = numel(findobj(f, 'Color', [1 0 0])); "
             "d = numel(findobj(f, '-depth', 1)); e = isempty(findobj(f, 'Tag', 'zzz')); "
             "p = numel(findobj(f, '-property', 'LineWidth')); fl = numel(findobj([l1 l2], 'flat', 'Tag', 'a'));")
    assert _v(s, "o").item() and _v(s, "n").item() == 4 and _v(s, "x").item() == 2
    assert _v(s, "r").item() == 1 and _v(s, "d").item() == 2 and _v(s, "e").item()
    assert _v(s, "p").item() == 3 and _v(s, "fl").item() == 1


def test_hidden_handles_and_findall():
    s = _run("set(l1, 'HandleVisibility', 'off'); a = numel(findobj(f, 'Type', 'line')); "
             "b = numel(findall(f, 'Type', 'line')); t = numel(findall(f, 'Type', 'text'));")
    assert _v(s, "a").item() == 1 and _v(s, "b").item() == 2 and _v(s, "t").item() >= 3


def test_ancestor_allchild_groot():
    s = _run("a = isequal(ancestor(l1, 'figure'), f); b = isequal(ancestor(l1, {'axes','figure'}), ax); "
             "c = isempty(ancestor(l1, 'legend')); k = allchild(ax); k1 = isequal(k(1), l2); "
             "g = strcmp(get(groot, 'Type'), 'root'); gf = isequal(get(groot, 'CurrentFigure'), f);")
    for n in ("a", "b", "c", "k1", "g", "gf"):
        assert _v(s, n).item(), n


@pytest.mark.parametrize("bad,msg", [
    ("findobj(f, 'Tag')", "needs a value"),
    ("findobj(f, '-bogus', 1)", "unknown option"),
    ("findobj(f, '-regexp', 'Tag', '(')", "regular expression"),
    ("ancestor(l1)", "Not enough input"),
])
def test_bad_queries_raise(bad, msg):
    with pytest.raises(Exception, match=msg):
        _run(bad)
