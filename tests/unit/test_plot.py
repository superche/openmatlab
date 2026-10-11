"""Plot MVP (Issue #5) — Agg / headless."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")
pytest.importorskip("matplotlib")

from openmatlab.graphics.matplotlib_backend import GraphicsError, MatplotlibGraphicsBackend
from openmatlab.host.plot_surface import HostPlotSurface
from openmatlab.host.repl import ReplSession
from openmatlab.numerics.numpy_backend import NumPyArrayBackend
from openmatlab.runtime.evaluator import Evaluator
from openmatlab.runtime.session import Session
from openmatlab.runtime.workspace import Workspace

pytestmark = [pytest.mark.unit, pytest.mark.needs_matplotlib, pytest.mark.needs_numpy]


def test_matplotlib_backend_plot_y_only():
    be = MatplotlibGraphicsBackend(interactive=False)
    n = NumPyArrayBackend()
    y = n.colon(1.0, 5.0)
    h = be.plot(y)
    assert float(h) == 1.0
    assert be.last_figure is not None
    ax = be.last_figure.axes[0]
    assert len(ax.lines) == 1
    be.close()


def test_matplotlib_backend_plot_xy_mismatch():
    be = MatplotlibGraphicsBackend(interactive=False)
    n = NumPyArrayBackend()
    with pytest.raises(GraphicsError):
        be.plot(n.colon(1.0, 3.0), n.colon(1.0, 4.0))


def test_host_surface_and_eval_builtin():
    graphics = MatplotlibGraphicsBackend(interactive=False)
    plots = HostPlotSurface(graphics)
    ws = Workspace()
    ev = Evaluator(workspace=ws, numerics=NumPyArrayBackend(), plots=plots)
    ev.eval_source("x = 1:5; y = x .* x; h = plot(x, y);")
    assert ws.get("h").is_scalar()
    assert float(ws.get("h").backend_buffer().reshape(-1)[0]) == 1.0
    assert len(graphics.last_figure.axes[0].lines) == 1


def test_session_default_plot_via_repl():
    s = Session.create_default()
    assert not isinstance(s.plots, type(None))
    ReplSession(s).run_line("plot(1:4);")
    # suppressed — still plotted
    backend = s.graphics
    assert backend is not None
    assert backend.last_figure is not None
