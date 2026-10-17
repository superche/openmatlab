"""#857 residuals delivered with G-E4 #771: colormap('name(n)'), title on a colorbar, @ishandle."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession

pytestmark = [pytest.mark.unit]


def _ws(code):
    s = ReplSession()
    s.run_line("figure('Visible','off'); " + code + " close all")
    return s.session.workspace


def test_colormap_expression_form_sets_size():
    w = _ws("colormap('bone(16)'); m = colormap; colormap('gray( 5 )'); g = colormap;")
    assert np.asarray(w.get("m").backend_buffer()).shape == (16, 3)
    np.testing.assert_allclose(np.asarray(w.get("g").backend_buffer())[:, 0], np.linspace(0, 1, 5))


def test_colorbar_title_and_ishandle_handle():
    w = _ws("hc = colorbar; t = title(hc, 'Temp'); s = t.String; f = @ishandle; ok = f(gcf);")
    assert w.get("s").text == "Temp"
    assert bool(np.asarray(w.get("ok").backend_buffer()).item())
