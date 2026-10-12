"""Minimal desktop shell — host-owned chrome that renders plugin panels.

KISS tkinter surface for M-plugins / Epic #349 acceptance demos. Plugins never
fork this shell; they contribute panel factories via ``window.register_panel``.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import List, Optional, Sequence

from openmatlab.extensions.host import PluginHost
from openmatlab.libs.path import ToolboxPath


def build_host(
    *,
    plugin_paths: Optional[Sequence[Path | str]] = None,
    activate: bool = True,
) -> PluginHost:
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    warns = host.discover(
        extra=list(plugin_paths) if plugin_paths else None,
        include_user_dir=False,
        include_entry_points=False,
    )
    for w in warns:
        print(f"warning: {w}")
    host.load_all()
    if activate:
        host.activate_on_startup()
    return host


def run_desktop(
    *,
    plugin_paths: Optional[Sequence[Path | str]] = None,
    demo_ms: Optional[int] = None,
    title: str = "OpenMATLAB Desktop (minimal)",
) -> PluginHost:
    """Open a tk main window with a notebook of contributed panels.

    ``demo_ms``: if set, auto-destroy after N milliseconds (screen recordings).
    """
    host = build_host(plugin_paths=plugin_paths, activate=True)
    root = tk.Tk()
    root.title(title)
    root.geometry("640x420")

    header = ttk.Frame(root, padding=8)
    header.pack(fill="x")
    ttk.Label(header, text=title, font=("", 14, "bold")).pack(side="left")
    # Prefer panels whose declarative ``when`` (if any) currently matches.
    allowed = {
        item.get("id")
        for item in host.list_panel_contributions(evaluate=True)
        if isinstance(item, dict) and item.get("id")
    }
    ids = [pid for pid in host.window_api.list_panels() if not allowed or pid in allowed]
    # If no declarative panel rows, fall back to all registered factories.
    if not allowed:
        ids = host.window_api.list_panels()
    ttk.Label(header, text=f"panels: {len(ids)}").pack(side="right")

    body = ttk.Notebook(root)
    body.pack(fill="both", expand=True, padx=8, pady=8)

    if not ids:
        empty = ttk.Frame(body, padding=16)
        ttk.Label(
            empty,
            text="No panels registered.\nPass --path demos/plugins/community.signal",
        ).pack()
        body.add(empty, text="(empty)")
    else:
        for pid in ids:
            tab = ttk.Frame(body)
            body.add(tab, text=pid.split(".")[-1])
            try:
                widget = host.window_api.create_panel(pid, tab)
                if isinstance(widget, (tk.Widget, ttk.Widget)):
                    widget.pack(fill="both", expand=True)
                else:
                    ttk.Label(tab, text=repr(widget)).pack(anchor="w")
            except Exception as exc:
                ttk.Label(tab, text=f"panel error: {exc}").pack(anchor="w")

    status = ttk.Label(
        root,
        text="Host-owned chrome · plugins fill panels slot · Epic #349 / #368",
        padding=6,
    )
    status.pack(fill="x")

    if demo_ms is not None and demo_ms > 0:
        root.after(int(demo_ms), root.destroy)

    root.mainloop()
    return host


def list_panel_summaries(
    plugin_paths: Optional[Sequence[Path | str]] = None,
) -> List[dict]:
    """Headless panel metadata (for tests / CLI without opening a window)."""
    host = build_host(plugin_paths=plugin_paths, activate=True)
    out: List[dict] = []
    for pid in host.window_api.list_panels():
        meta = host.window_api.create_panel(pid, None)
        if isinstance(meta, dict):
            row = dict(meta)
            row.setdefault("id", pid)
            out.append(row)
        else:
            out.append({"id": pid, "repr": repr(meta)})
    return out
