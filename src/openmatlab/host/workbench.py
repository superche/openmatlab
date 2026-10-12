"""MATLAB-aligned Workbench — Host product chrome using plugin slots.

Host owns layout regions (command window, editor, workspace browser, current
folder, figures). Plugins contribute additional panels via the extensions
``panels`` slot; they never fork this shell (PLUGIN-CONTRACT).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

from openmatlab.host.display import ConsoleDisplay
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session
from openmatlab.runtime.value import Value

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
class WorkspaceRow:
    """One workspace browser row (W04): name / size / class."""

    name: str
    size: str
    matlab_class: str


@dataclass
class FolderEntry:
    """One Current Folder listing row (W05)."""

    name: str
    kind: str  # "dir" | "file"
    is_mfile: bool = False


@dataclass
class FigureInfo:
    """One open figure (W06)."""

    handle: float
    title: str


def _value_size_str(val: Value) -> str:
    shape = getattr(val, "shape", None)
    if shape is not None:
        return "x".join(str(int(d)) for d in shape)
    text = getattr(val, "text", None)
    if isinstance(text, str):
        return f"1x{len(text)}"
    return "1x1"


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
class EditorPanel:
    """Editor MVP — open / edit / save ``.m`` files (W03)."""

    path: Optional[Path] = None
    text: str = ""
    dirty: bool = False

    def open_file(self, path: Path | str) -> str:
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Editor.open_file: not a file: {p}")
        self.text = p.read_text(encoding="utf-8")
        self.path = p
        self.dirty = False
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text
        self.dirty = True

    def save(self, path: Optional[Path | str] = None) -> Path:
        if path is not None:
            target = Path(path).expanduser().resolve()
        elif self.path is not None:
            target = self.path
        else:
            raise ValueError("Editor.save: no path (open a file or pass path=)")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.text, encoding="utf-8")
        self.path = target
        self.dirty = False
        return target

    @property
    def is_open(self) -> bool:
        return self.path is not None


@dataclass
class WorkspaceBrowser:
    """Workspace browser — name/size/class + refresh (W04)."""

    session: Session

    def rows(self) -> List[WorkspaceRow]:
        out: List[WorkspaceRow] = []
        for name in sorted(n for n in self.session.workspace.names() if n != "ans"):
            val = self.session.workspace.get(name)
            out.append(
                WorkspaceRow(
                    name=name,
                    size=_value_size_str(val),
                    matlab_class=val.matlab_class(),
                )
            )
        return out

    def refresh(self) -> List[WorkspaceRow]:
        return self.rows()

    def as_table(self) -> str:
        lines = [f"{'Name':<16} {'Size':<12} Class"]
        lines.append("-" * 40)
        for r in self.rows():
            lines.append(f"{r.name:<16} {r.size:<12} {r.matlab_class}")
        return "\n".join(lines)


@dataclass
class CurrentFolderBrowser:
    """Current Folder — list cwd, cd, open ``.m`` into Editor (W05)."""

    _cwd: Path = field(default_factory=lambda: Path.cwd())

    @classmethod
    def create(cls, cwd: Optional[Path | str] = None) -> "CurrentFolderBrowser":
        root = Path(cwd).expanduser().resolve() if cwd is not None else Path.cwd()
        return cls(_cwd=root)

    def pwd(self) -> Path:
        return self._cwd

    def cd(self, path: Path | str) -> Path:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = (self._cwd / target).resolve()
        else:
            target = target.resolve()
        if not target.is_dir():
            raise NotADirectoryError(f"CurrentFolder.cd: not a directory: {target}")
        self._cwd = target
        return self._cwd

    def list_entries(self) -> List[FolderEntry]:
        entries: List[FolderEntry] = []
        try:
            children = sorted(self._cwd.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return entries
        for child in children:
            if child.name.startswith("."):
                continue
            if child.is_dir():
                entries.append(FolderEntry(name=child.name, kind="dir"))
            elif child.is_file():
                entries.append(
                    FolderEntry(
                        name=child.name,
                        kind="file",
                        is_mfile=child.suffix.lower() == ".m",
                    )
                )
        return entries

    def open_mfile(self, name: str, editor: EditorPanel) -> str:
        """Open a ``.m`` file from cwd into the Editor panel."""
        path = (self._cwd / name).resolve()
        if path.suffix.lower() != ".m":
            raise ValueError(f"CurrentFolder.open_mfile: expected .m, got {path.name}")
        return editor.open_file(path)


@dataclass
class FigureManager:
    """Figure management via PlotSurface / GraphicsBackend (W06)."""

    session: Session

    def list_figures(self) -> List[FigureInfo]:
        plots = self.session.plots
        list_fn = getattr(plots, "list_figures", None)
        raw: Sequence[Tuple[float, str]]
        if callable(list_fn):
            raw = list_fn()
        else:
            raw = []
        return [FigureInfo(handle=float(h), title=str(t)) for h, t in raw]

    def close(self, handle: Optional[float] = None) -> None:
        self.session.plots.close(handle)

    def focus(self, handle: float) -> None:
        focus_fn = getattr(self.session.plots, "focus", None)
        if not callable(focus_fn):
            raise NotImplementedError("FigureManager.focus: PlotSurface has no focus")
        focus_fn(handle)

    def as_table(self) -> str:
        lines = [f"{'Handle':<10} Title"]
        lines.append("-" * 40)
        for fig in self.list_figures():
            lines.append(f"{fig.handle:<10g} {fig.title}")
        if len(lines) == 2:
            lines.append("(no open figures)")
        return "\n".join(lines)


@dataclass
class Workbench:
    """Host-owned workbench: layout registry + host panels + plugin slots."""

    command_window: CommandWindow
    editor: EditorPanel
    workspace_browser: WorkspaceBrowser
    current_folder: CurrentFolderBrowser
    figures: FigureManager
    plugin_paths: List[Path] = field(default_factory=list)
    _plugin_host: Any = None

    @classmethod
    def create(
        cls,
        *,
        plugin_paths: Optional[Sequence[Path | str]] = None,
        activate_plugins: bool = False,
        cwd: Optional[Path | str] = None,
    ) -> "Workbench":
        cw = CommandWindow.create()
        paths = [Path(p) for p in (plugin_paths or [])]
        wb = cls(
            command_window=cw,
            editor=EditorPanel(),
            workspace_browser=WorkspaceBrowser(session=cw.session),
            current_folder=CurrentFolderBrowser.create(cwd=cwd),
            figures=FigureManager(session=cw.session),
            plugin_paths=paths,
        )
        if activate_plugins and paths:
            wb._ensure_plugins(activate=True)
        return wb

    def eval(self, source: str) -> str:
        """Command Window eval; workspace browser reflects side effects."""
        return self.command_window.eval(source)

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
                "ready",
                "open/edit/save .m (W03)",
            ),
            RegionSpec(
                "workspace_browser",
                "Workspace",
                "host",
                "ready",
                "name/size/class + refresh (W04)",
            ),
            RegionSpec(
                "current_folder",
                "Current Folder",
                "host",
                "ready",
                "list/cd/open .m (W05)",
            ),
            RegionSpec(
                "figures",
                "Figures",
                "host",
                "ready",
                "list/close/focus via PlotSurface (W06)",
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
        """Minimal tk chrome: Command Window + host panels (editor/ws/folder/figs)."""
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk

        if self.plugin_paths and self._plugin_host is None:
            self._ensure_plugins(activate=True)

        root = tk.Tk()
        root.title(title)
        root.geometry("980x600")

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

        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

        # --- Editor tab ---
        tab_ed = ttk.Frame(nb, padding=6)
        nb.add(tab_ed, text="Editor")
        ed_path_var = tk.StringVar(value="(no file)")
        ttk.Label(tab_ed, textvariable=ed_path_var).pack(anchor="w")
        ed_text = tk.Text(tab_ed, height=16, wrap="none", font=("Courier", 10))
        ed_text.pack(fill="both", expand=True)

        def _sync_editor_ui() -> None:
            ed_path_var.set(str(self.editor.path) if self.editor.path else "(no file)")
            ed_text.delete("1.0", "end")
            ed_text.insert("1.0", self.editor.text)

        def ed_open() -> None:
            path = filedialog.askopenfilename(
                title="Open .m file",
                filetypes=[("MATLAB files", "*.m"), ("All", "*.*")],
                initialdir=str(self.current_folder.pwd()),
            )
            if not path:
                return
            self.editor.open_file(path)
            _sync_editor_ui()

        def ed_save() -> None:
            self.editor.set_text(ed_text.get("1.0", "end-1c"))
            try:
                if self.editor.path is None:
                    path = filedialog.asksaveasfilename(
                        defaultextension=".m",
                        filetypes=[("MATLAB files", "*.m")],
                        initialdir=str(self.current_folder.pwd()),
                    )
                    if not path:
                        return
                    self.editor.save(path)
                else:
                    self.editor.save()
                _sync_editor_ui()
            except Exception as exc:
                messagebox.showerror("Editor", str(exc))

        ed_btns = ttk.Frame(tab_ed)
        ed_btns.pack(fill="x", pady=4)
        ttk.Button(ed_btns, text="Open…", command=ed_open).pack(side="left", padx=2)
        ttk.Button(ed_btns, text="Save", command=ed_save).pack(side="left", padx=2)

        # --- Workspace tab ---
        tab_ws = ttk.Frame(nb, padding=6)
        nb.add(tab_ws, text="Workspace")
        ws_tree = ttk.Treeview(tab_ws, columns=("size", "class"), show="tree headings", height=14)
        ws_tree.heading("#0", text="Name")
        ws_tree.heading("size", text="Size")
        ws_tree.heading("class", text="Class")
        ws_tree.column("#0", width=120)
        ws_tree.column("size", width=80)
        ws_tree.column("class", width=80)
        ws_tree.pack(fill="both", expand=True)

        def refresh_ws() -> None:
            ws_tree.delete(*ws_tree.get_children())
            for row in self.workspace_browser.refresh():
                ws_tree.insert("", "end", text=row.name, values=(row.size, row.matlab_class))

        ttk.Button(tab_ws, text="Refresh", command=refresh_ws).pack(anchor="e", pady=4)

        # --- Current Folder tab ---
        tab_cf = ttk.Frame(nb, padding=6)
        nb.add(tab_cf, text="Current Folder")
        cf_pwd = tk.StringVar(value=str(self.current_folder.pwd()))
        ttk.Label(tab_cf, textvariable=cf_pwd).pack(anchor="w")
        cf_list = tk.Listbox(tab_cf, height=12)
        cf_list.pack(fill="both", expand=True)
        cf_entry = ttk.Entry(tab_cf)
        cf_entry.pack(fill="x", pady=4)

        def refresh_cf() -> None:
            cf_pwd.set(str(self.current_folder.pwd()))
            cf_list.delete(0, "end")
            for e in self.current_folder.list_entries():
                mark = "[dir] " if e.kind == "dir" else ("[m]   " if e.is_mfile else "      ")
                cf_list.insert("end", f"{mark}{e.name}")

        def cf_cd(_event=None) -> None:
            target = cf_entry.get().strip()
            if not target:
                return
            try:
                self.current_folder.cd(target)
                cf_entry.delete(0, "end")
                refresh_cf()
            except Exception as exc:
                messagebox.showerror("Current Folder", str(exc))

        def cf_open_selected(_event=None) -> None:
            sel = cf_list.curselection()
            if not sel:
                return
            raw = cf_list.get(sel[0])
            name = raw.split(None, 1)[-1] if raw.startswith("[") else raw.strip()
            entries = {e.name: e for e in self.current_folder.list_entries()}
            ent = entries.get(name)
            if ent is None:
                return
            if ent.kind == "dir":
                self.current_folder.cd(name)
                refresh_cf()
            elif ent.is_mfile:
                self.current_folder.open_mfile(name, self.editor)
                _sync_editor_ui()
                nb.select(tab_ed)

        cf_btns = ttk.Frame(tab_cf)
        cf_btns.pack(fill="x")
        ttk.Button(cf_btns, text="cd", command=cf_cd).pack(side="left", padx=2)
        ttk.Button(cf_btns, text="Refresh", command=refresh_cf).pack(side="left", padx=2)
        ttk.Button(cf_btns, text="Open .m", command=cf_open_selected).pack(side="left", padx=2)
        cf_entry.bind("<Return>", cf_cd)
        cf_list.bind("<Double-Button-1>", cf_open_selected)

        # --- Figures tab ---
        tab_fig = ttk.Frame(nb, padding=6)
        nb.add(tab_fig, text="Figures")
        fig_list = tk.Listbox(tab_fig, height=12)
        fig_list.pack(fill="both", expand=True)

        def refresh_figs() -> None:
            fig_list.delete(0, "end")
            for info in self.figures.list_figures():
                fig_list.insert("end", f"{info.handle:g}  {info.title}")

        def _selected_handle() -> Optional[float]:
            sel = fig_list.curselection()
            if not sel:
                return None
            return float(fig_list.get(sel[0]).split()[0])

        def fig_close() -> None:
            h = _selected_handle()
            self.figures.close(h)
            refresh_figs()

        def fig_focus() -> None:
            h = _selected_handle()
            if h is None:
                return
            try:
                self.figures.focus(h)
            except Exception as exc:
                messagebox.showerror("Figures", str(exc))

        fig_btns = ttk.Frame(tab_fig)
        fig_btns.pack(fill="x", pady=4)
        ttk.Button(fig_btns, text="Refresh", command=refresh_figs).pack(side="left", padx=2)
        ttk.Button(fig_btns, text="Close", command=fig_close).pack(side="left", padx=2)
        ttk.Button(fig_btns, text="Focus", command=fig_focus).pack(side="left", padx=2)

        # Plugin / layout summary tabs for any extra regions
        for r in self.regions():
            if r.kind != "plugin":
                continue
            tab = ttk.Frame(nb, padding=8)
            nb.add(tab, text=r.title[:16])
            ttk.Label(
                tab,
                text=f"{r.id}\nkind={r.kind}  status={r.status}\n{r.notes}",
                justify="left",
            ).pack(anchor="w")

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
            refresh_ws()
            refresh_figs()

        entry.bind("<Return>", on_eval)
        ttk.Button(left, text="Eval", command=on_eval).pack(anchor="e")

        refresh_ws()
        refresh_cf()
        refresh_figs()
        _sync_editor_ui()

        def _demo_eval(line: str) -> None:
            out.insert("end", f">> {line}\n")
            try:
                text = self.command_window.eval(line)
                if text:
                    out.insert("end", text)
            except Exception as exc:
                out.insert("end", f"Error: {exc}\n")
            out.see("end")
            refresh_ws()
            refresh_figs()

        def _schedule_demo() -> None:
            """Scripted walkthrough for showcase recordings (--demo-ms)."""
            sample = self.current_folder.pwd() / "showcase_demo.m"
            if not sample.is_file():
                sample.parent.mkdir(parents=True, exist_ok=True)
                sample.write_text("% showcase demo\nx = 1:5;\ny = x .* x;\n", encoding="utf-8")
                refresh_cf()

            root.after(600, lambda: (_demo_eval("a = [1 2 3 4];"), nb.select(tab_ws)))
            root.after(1400, lambda: _demo_eval("b = a .* 2"))
            root.after(2200, lambda: (nb.select(tab_cf), refresh_cf()))
            root.after(
                3000,
                lambda: (
                    self.current_folder.open_mfile("showcase_demo.m", self.editor),
                    _sync_editor_ui(),
                    nb.select(tab_ed),
                ),
            )
            root.after(4200, lambda: (_demo_eval("plot(1:8);"), nb.select(tab_fig)))
            root.after(5200, lambda: _demo_eval("plot(1:4);"))
            root.after(6000, refresh_figs)

        if demo_ms is not None and demo_ms > 0:
            root.after(200, _schedule_demo)
            root.after(int(demo_ms), root.destroy)
        root.mainloop()
