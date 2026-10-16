"""Epic #771 (M13 G-E4): 3-D plotting, colour/image helpers, tick helpers."""

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


def test_plot3_surf_mesh_view_zlim():
    s = _run("l = plot3(1:3, 1:3, [2 4 6]); z = l.ZData; v = view; [X, Y] = meshgrid(1:3); "
             "h = surf(X, Y, X + Y); c = class(h); m = mesh(X, Y, X .* Y); mt = m.Type; zl = zlim; "
             "view(2); v2 = view; view(45, 10); [az, el] = view; zlim([0 10]); z2 = zlim;")
    assert _v(s, "z").tolist() == [[2, 4, 6]] and _v(s, "v").tolist() == [[-37.5, 30]]
    assert _t(s, "c") == "matlab.graphics.chart.primitive.Surface" and _t(s, "mt") == "surface"
    assert _v(s, "zl").tolist() == [[1, 9]] and _v(s, "v2").tolist() == [[0, 90]]
    assert _v(s, "az").item() == 45 and _v(s, "el").item() == 10 and _v(s, "z2").tolist() == [[0, 10]]


def test_pcolor_and_surface_stay_primitive():
    s = _run("p = pcolor(magic(3)); c = class(p);")
    assert _t(s, "c") == "matlab.graphics.primitive.Surface"


def test_sphere_cylinder_outputs_and_plots():
    s = _run("[x, y, z] = sphere(4); n = size(x); r = max(abs(sqrt(x.^2 + y.^2 + z.^2) - 1), [], 'all'); "
             "[a, b, c] = cylinder([1 2], 6); m = size(a); sphere; k = numel(findobj(gca, 'Type', 'surface'));")
    assert _v(s, "n").tolist() == [[5, 5]] and _v(s, "r").item() < 1e-12
    assert _v(s, "m").tolist() == [[2, 7]] and _v(s, "k").item() == 1


def test_scatter3_bar3_shading_light():
    s = _run("h = scatter3(1:3, 1:3, 1:3); z = h.ZData; b = bar3([1 2 3]); surf(peaks(5)); shading interp; "
             "f = get(findobj(gca, 'Type', 'surface'), 'FaceColor'); lt = light; t = lt.Type; lighting gouraud;")
    assert _v(s, "z").tolist() == [[1, 2, 3]] and _t(s, "f") == "interp" and _t(s, "t") == "light"


def test_imshow_ticks_aspect_uistack():
    s = _run("im = imshow(uint8([0 255; 128 64])); t = im.Type; plot(1:10); xticks([1 5 10]); xt = xticks; "
             "yticklabels({'a','b'}); yl = yticklabels; daspect([1 2 1]); d = daspect; "
             "a = plot(1:3); hold on; b = plot(3:-1:1); uistack(a, 'top'); k = get(gca, 'Children'); top = isequal(k(1), a);")
    assert _t(s, "t") == "image" and _v(s, "xt").tolist() == [[1, 5, 10]]
    assert s.workspace.get("yl").get(0, 1).text == "b" and _v(s, "d").tolist() == [[1, 2, 1]] and _v(s, "top").item()


def test_intrinsic_function_handles():
    s = _run("f = @ishandle; a = f(gcf); g = @isvarname; b = g('x1'); c = cellfun(@isvarname, {'a', '1'});")
    assert _v(s, "a").item() and _v(s, "b").item() and _v(s, "c").tolist() == [[True, False]]


@pytest.mark.parametrize("bad,msg", [
    ("plot3(1:3, 1:3)", "Not enough input"),
    ("plot3(1:3, 1:3, 1:2)", "same length"),
    ("surf([1 2; 3 4], [1 2], [1 2 3; 4 5 6])", "dimensions must agree"),
    ("view(7)", "must be 2 or 3"),
    ("zlim([2 1])", "second element is larger"),
    ("shading wobbly", "shading: option"),
    ("xticks([3 1])", "increasing"),
    ("imshow('cat.png')", "image data required"),
    ("sphere(0)", "positive integer"),
])
def test_bad_calls_raise(bad, msg):
    with pytest.raises(Exception, match=msg):
        _run(bad)
