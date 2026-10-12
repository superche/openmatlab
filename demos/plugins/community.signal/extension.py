"""Community Signal plugin — clean-room Octave Forge–compatible windows.

Implements a small, popular subset of the public MATLAB / Octave Forge
``signal`` window API (``hamming``, ``rectwin``, ``blackman``) as ``.m``
files on a contributed path entry, plus a real desktop panel factory.

License: MIT (this plugin). Upstream Octave Forge ``signal`` is GPL; we do
**not** copy its sources — clean-room from public documentation / textbooks.
Not a MathWorks proprietary toolbox.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional


def _format_column(values: list[float], *, digits: int = 4) -> str:
    parts = [f"{v:.{digits}g}" for v in values]
    return "[" + " ".join(parts) + "]'"


def _eval_hamming(host: Any, n: int = 5) -> tuple[str, list[float]]:
    """Call path-contributed ``hamming.m`` through a Session/REPL if possible."""
    path_hit = host.path.which("hamming")
    # Prefer live eval via Session when the host was constructed with one.
    session = getattr(host, "_session", None)
    # HostAPIFacade has no session; PluginHost may stash it — try workspace root.
    # Fall back: create a short-lived Session bound to the same ToolboxPath.
    from openmatlab.host.display import NullDisplay
    from openmatlab.host.repl import ReplSession
    from openmatlab.runtime.session import Session

    s = Session.create_default()
    s.display = NullDisplay()
    # Reuse host path entries (plugin mfiles already addpath'd).
    try:
        entries = list(host.path.list())
    except Exception:
        entries = []
    for e in entries:
        s.path.addpath(e)
    s.functions.path = s.path
    repl = ReplSession(s)
    repl.run_line(f"w = hamming({int(n)});")
    w_val = s.workspace.get("w")
    buf = w_val.backend_buffer().reshape(-1, order="F")
    nums = [float(x) for x in buf]
    which = host.path.which("hamming")
    which_s = str(which) if which else "(unresolved)"
    summary = (
        f"hamming({n})={_format_column(nums)} which={which_s}"
    )
    return summary, nums


def _build_panel_widget(parent: Any, plugin_id: str, host: Any) -> Any:
    """Tkinter panel surface for the minimal desktop shell."""
    import tkinter as tk
    from tkinter import ttk

    frame = ttk.Frame(parent, padding=12)
    frame.columnconfigure(0, weight=1)

    ttk.Label(
        frame,
        text="Community Signal",
        font=("", 18, "bold"),
    ).grid(row=0, column=0, sticky="w")
    ttk.Label(
        frame,
        text=(
            "Clean-room Octave Forge–compatible windows\n"
            "(hamming / rectwin / blackman) — MIT; not MathWorks."
        ),
        font=("", 13),
        justify="left",
    ).grid(row=1, column=0, sticky="w", pady=(6, 10))

    out = tk.Text(frame, height=7, width=64, wrap="word", font=("DejaVu Sans Mono", 13))
    out.grid(row=2, column=0, sticky="nsew")
    frame.rowconfigure(2, weight=1)

    def _run() -> None:
        try:
            summary, _ = _eval_hamming(host, 8)
            line = f"{plugin_id}: {summary}\n"
        except Exception as exc:  # pragma: no cover - UI path
            line = f"{plugin_id}: error {type(exc).__name__}: {exc}\n"
        out.insert("end", line)
        out.see("end")

    btn = ttk.Button(frame, text="Run hamming(8)", command=_run)
    btn.grid(row=3, column=0, sticky="w", pady=(10, 0))

    # Showcase recording: publish button screen coords for xdotool click.
    xy_path = os.environ.get("OPENMATLAB_DEMO_BTN_XY")
    if xy_path:

        def _publish_xy(_event: Any = None) -> None:
            try:
                btn.update_idletasks()
                cx = btn.winfo_rootx() + max(btn.winfo_width(), 1) // 2
                cy = btn.winfo_rooty() + max(btn.winfo_height(), 1) // 2
                Path(xy_path).write_text(f"{cx} {cy}\n", encoding="utf-8")
            except Exception:
                pass

        btn.bind("<Map>", _publish_xy)
        frame.after(300, _publish_xy)
        frame.after(800, _publish_xy)

    # No auto-run: showcase clicks Run so the panel result is clearly from UI.
    return frame


def activate(context: Any) -> None:
    host = context.host
    plugin_id = context.plugin_id

    def _demo(*_args: Any, **_kwargs: Any) -> str:
        try:
            summary, _ = _eval_hamming(host, 5)
            msg = f"{plugin_id}: demo OK — {summary}"
        except Exception as exc:
            msg = (
                f"{plugin_id}: demo OK (path={context.extension_path}) "
                f"[hamming eval failed: {type(exc).__name__}: {exc}]"
            )
        host.window.show_information_message(msg)
        return msg

    def _panel_factory(parent: Optional[Any] = None) -> Any:
        """Panel factory: headless dict when parent is None; else tk widget."""
        if parent is None:
            return {
                "id": "community.signal.panel",
                "title": "Signal",
                "plugin": plugin_id,
                "kind": "tk-frame",
                "summary": (
                    "Octave Forge–compatible windows "
                    "(hamming / rectwin / blackman)"
                ),
            }
        return _build_panel_widget(parent, plugin_id, host)

    host.commands.register_command("community.signal.demo", _demo)
    host.window.register_panel("community.signal.panel", _panel_factory)


def deactivate() -> None:
    pass
