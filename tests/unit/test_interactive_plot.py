"""Interactive plot policy (Issue #23) — headless unit tests."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("numpy")

from openmatlab.graphics.matplotlib_backend import MatplotlibGraphicsBackend
from openmatlab.host.plot_surface import HostPlotSurface
from openmatlab.host.repl import ReplSession
from openmatlab.numerics.numpy_backend import NumPyArrayBackend
from openmatlab.runtime.session import Session, resolve_interactive_plots

pytestmark = [pytest.mark.unit, pytest.mark.needs_matplotlib, pytest.mark.needs_numpy]


def test_resolve_interactive_respects_ci(monkeypatch):
    monkeypatch.setenv("OPENMATLAB_PLOT_INTERACTIVE", "1")
    monkeypatch.setenv("CI", "true")
    assert resolve_interactive_plots() is False
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert resolve_interactive_plots() is True
    assert resolve_interactive_plots(False) is False
    assert resolve_interactive_plots(True) is True


def test_default_session_is_agg_in_ci(monkeypatch):
    monkeypatch.setenv("CI", "1")
    monkeypatch.setenv("OPENMATLAB_PLOT_INTERACTIVE", "1")
    s = Session.create_default()
    assert s.graphics is not None
    assert s.graphics.interactive is False


def test_explicit_interactive_flag():
    s = Session.create_default(interactive_plots=True)
    assert s.graphics.interactive is True
    s2 = Session.create_default(interactive_plots=False)
    assert s2.graphics.interactive is False


def test_show_noop_under_agg():
    be = MatplotlibGraphicsBackend(interactive=False)
    n = NumPyArrayBackend()
    be.plot(n.colon(1.0, 3.0))
    HostPlotSurface(be).show()  # must not raise


def test_language_show_after_plot():
    s = Session.create_default(interactive_plots=False)
    ReplSession(s).run_line("plot(1:3);")
    ReplSession(s).run_line("show();")
    assert float(s.workspace.get("ans").backend_buffer().reshape(-1)[0]) == 1.0


def test_drawnow_alias():
    s = Session.create_default(interactive_plots=False)
    ReplSession(s).run_line("plot(1:2); drawnow();")
