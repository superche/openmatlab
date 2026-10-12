"""MATLAB-aligned Workbench — Host product chrome using plugin slots.

Host owns layout regions (command window, editor, workspace browser, current
folder, figures). Plugins contribute additional panels via the extensions
``panels`` slot; they never fork this shell (PLUGIN-CONTRACT).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from openmatlab.host.display import ConsoleDisplay
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

# Named host-owned layout regions (W01).
HOST_REGIONS = (
    "command_window",
    "editor",
    "workspace_browser",
    "current_folder",
    "figures",
)


@dataclass
class RegionSpec:
    """Descriptor for a workbench layout region."""

    id: str
    title: str
    kind: str  # "host" | "plugin"
    status: str  # "ready" | "stub"
    notes: str = ""


@dataclass
class CommandWindow:
    """Headless Command Window — eval lines via ReplSession (W02)."""

    session: Session
    repl: ReplSession
    _stream: io.StringIO = field(default_factory=io.StringIO)

    @classmethod
    def create(cls, session: Optional[Session] = None) -> "CommandWindow":
        s = session if session is not None else Session.create_default()
        buf = io.StringIO()
        s.display = ConsoleDisplay(workspace=s.workspace, stream=buf)
        return cls(session=s, repl=ReplSession(s), _stream=buf)

    def eval(self, source: str) -> str:
        """Evaluate one or more statements; return captured display text."""
        before = self._stream.tell()
        self.repl.run_line(source)
        self._stream.seek(before)
        return self._stream.read()

    def workspace_names(self) -> List[str]:
        return sorted(n for n in self.session.workspace.names() if n != "ans")


@dataclass
class Workbench:
    """Host-owned workbench: layout registry + Command Window + plugin slots."""

    command_window: CommandWindow
    plugin_paths: List[Path] = field(default_factory=list)
    _plugin_host: Any = None

    @classmethod
    def create(
        cls,
        *,
        plugin_paths: Optional[Sequence[Path | str]] = None,
        activate_plugins: bool = False,
    ) -> "Workbench":
        cw = CommandWindow.create()
        paths = [Path(p) for p in (plugin_paths or [])]
        wb = cls(command_window=cw, plugin_paths=paths)
        if activate_plugins and paths:
            wb._ensure_plugins(activate=True)
        return wb

    def regions(self) -> List[RegionSpec]:
        """Host layout regions + any discovered plugin panels."""
        specs = [
            RegionSpec(
                "command_window",
                "Command Window",
                "host",
                "ready",
                "ReplSession eval + display capture",
            ),
            RegionSpec(
                "editor",
                "Editor",
                "host",
                "stub",
                "W03 pending",
            ),
            RegionSpec(
                "workspace_browser",
                "Workspace",
                "host",
                "stub",
                "W04 pending",
            ),
            RegionSpec(
                "current_folder",
                "Current Folder",
                "host",
                "stub",
                "W05 pending",
            ),
            RegionSpec(
                "figures",
                "Figures",
                "host",
                "stub",
                "W06 pending",
            ),
        ]
        if self._plugin_host is not None:
            for pid in self._plugin_host.window_api.list_panels():
                specs.append(
                    RegionSpec(
                        pid,
                        pid.split(".")[-1],
                        "plugin",
                        "ready",
                        "contributed via panels slot",
                    )
                )
        return specs

    def list_regions_table(self) -> str:
        lines = [f"{'ID':<28} {'TITLE':<18} {'KIND':<8} STATUS"]
        lines.append("-" * 70)
        for r in self.regions():
            lines.append(f"{r.id:<28} {r.title:<18} {r.kind:<8} {r.status}")
        return "\n".join(lines)

    def _ensure_plugins(self, *, activate: bool) -> None:
        from openmatlab.extensions.host import PluginHost
        from openmatlab.libs.path import ToolboxPath

        host = PluginHost(toolbox_path=ToolboxPath())
        host.bind_apis()
        host.discover(
            extra=self.plugin_paths or None,
            include_user_dir=False,
            include_entry_points=False,
        )
        host.load_all()
        if activate:
            host.activate_on_startup()
        self._plugin_host = host

    def run_tk(self, *, demo_ms: Optional[int] = None, title: str = "OpenMATLAB Workbench") -> None:
        """Minimal tk chrome: Command Window + notebook of host/plugin regions."""
        import tkinter as tk
        from tkinter import ttk

        if self.plugin_paths and self._plugin_host is None:
            self._ensure_plugins(activate=True)

        root = tk.Tk()
        root.title(title)
        root.geometry("800x520")

        paned = ttk.Panedwindow(root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        left = ttk.Frame(paned, padding=4)
        right = ttk.Frame(paned, padding=4)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        ttk.Label(left, text="Command Window", font=("", 11, "bold")).pack(anchor="w")
        out = tk.Text(left, height=18, wrap="word")
        out.pack(fill="both", expand=True)
        entry = ttk.Entry(left)
        entry.pack(fill="x", pady=4)

        def on_eval(_event=None) -> None:
            line = entry.get().strip()
            if not line:
                return
            entry.delete(0, "end")
            out.insert("end", f">> {line}\n")
            try:
                text = self.command_window.eval(line)
                if text:
                    out.insert("end", text)
            except Exception as exc:
                out.insert("end", f"Error: {exc}\n")
            out.see("end")

        entry.bind("<Return>", on_eval)
        ttk.Button(left, text="Eval", command=on_eval).pack(anchor="e")

        ttk.Label(right, text="Layout", font=("", 11, "bold")).pack(anchor="w")
        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)
        for r in self.regions():
            tab = ttk.Frame(nb, padding=8)
            nb.add(tab, text=r.title[:16])
            ttk.Label(
                tab,
                text=f"{r.id}\nkind={r.kind}  status={r.status}\n{r.notes}",
                justify="left",
            ).pack(anchor="w")

        if demo_ms is not None and demo_ms > 0:
            root.after(int(demo_ms), root.destroy)
        root.mainloop()
