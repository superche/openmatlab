"""#367 — real community toolbox call + #368 panel surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.extensions.host import PluginHost
from openmatlab.host.desktop import list_panel_summaries
from openmatlab.libs.path import ToolboxPath

pytestmark = pytest.mark.unit

SAMPLE = Path("demos/plugins/community.signal")


def _activated_host() -> PluginHost:
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    host.discover(
        extra=[SAMPLE], include_user_dir=False, include_entry_points=False
    )
    host.load_all()
    host.activate_on_startup()
    return host


def test_hamming_which_and_demo_calls_real_window():
    host = _activated_host()
    hit = host.path_api.which("hamming")
    assert hit is not None
    assert hit.name == "hamming.m"
    result = host.execute_command("community.signal.demo")
    assert "demo OK" in result
    assert "hamming(5)=" in result
    assert "0.08" in result
    assert "which=" in result


def test_rectwin_and_blackman_on_path():
    host = _activated_host()
    assert host.path_api.which("rectwin") is not None
    assert host.path_api.which("blackman") is not None


def test_panel_factory_headless_metadata():
    host = _activated_host()
    assert "community.signal.panel" in host.window_api.list_panels()
    meta = host.window_api.create_panel("community.signal.panel", None)
    assert isinstance(meta, dict)
    assert meta["title"] == "Signal"
    assert "hamming" in meta["summary"]


def test_list_panel_summaries_helper():
    rows = list_panel_summaries([SAMPLE])
    assert any(r.get("id") == "community.signal.panel" for r in rows)


def test_panel_factory_builds_tk_widget():
    import os

    import pytest

    if not os.environ.get("DISPLAY"):
        pytest.skip("tk panel widget requires DISPLAY (headless CI uses --list-only)")

    import tkinter as tk

    host = _activated_host()
    root = tk.Tk()
    root.withdraw()
    try:
        widget = host.window_api.create_panel("community.signal.panel", root)
        assert isinstance(widget, (tk.Widget,))
    finally:
        root.destroy()
