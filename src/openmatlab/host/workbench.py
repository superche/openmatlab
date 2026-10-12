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

# Classic MATLAB Desktop dock slots (W09). Values: top|left|center|bottom|right.
DEFAULT_DOCK: dict[str, str] = {
    "menu_bar": "top",
    "toolstrip": "top",
    "path_toolbar": "top",
    "current_folder": "left",
    "editor": "center",
    "command_window": "bottom",
    "workspace_browser": "right",
    "figures": "right",
}

# Menu bar model (W07) — labels only; tk wires commands.
MENU_BAR_SPEC: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("File", ("New Script", "Open…", "Save", "Close Document", "Exit")),
    ("Edit", ("Cut", "Copy", "Paste")),
    ("View", ("Command Window", "Workspace", "Current Folder", "Figures")),
    ("Layout", ("Default",)),
)

# Toolstrip / toolbar Home actions (W08).
TOOLBAR_SPEC: Tuple[str, ...] = (
    "New Script",
    "Open…",
    "Save",
    "Run",
)

LAYOUT_PRESETS: Tuple[str, ...] = ("default",)


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
    """One workspace browser row (W04/W12): name / value / size / class."""

    name: str
    size: str
    matlab_class: str
    value: str = ""


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


def _value_preview(val: Value, *, max_len: int = 48) -> str:
    """Short Value column preview (W12)."""
    text = getattr(val, "text", None)
    if isinstance(text, str):
        shown = repr(text)
        return shown if len(shown) <= max_len else shown[: max_len - 3] + "..."
    buf_fn = getattr(val, "backend_buffer", None)
    if callable(buf_fn):
        try:
            raw = str(buf_fn()).replace("\n", " ")
            return raw if len(raw) <= max_len else raw[: max_len - 3] + "..."
        except Exception:
            pass
    return val.matlab_class()


@dataclass
class CommandWindow:
    """Headless Command Window — eval lines via ReplSession (W02/W11)."""

    session: Session
    repl: ReplSession
    _stream: io.StringIO = field(default_factory=io.StringIO)
    _history: List[str] = field(default_factory=list)

    @classmethod
    def create(cls, session: Optional[Session] = None) -> "CommandWindow":
        s = session if session is not None else Session.create_default()
        buf = io.StringIO()
        s.display = ConsoleDisplay(workspace=s.workspace, stream=buf)
        return cls(session=s, repl=ReplSession(s), _stream=buf)

    def eval(self, source: str) -> str:
        """Evaluate one or more statements; return captured display text."""
        line = source.strip()
        if line:
            self._history.append(line)
        before = self._stream.tell()
        self.repl.run_line(source)
        self._stream.seek(before)
        return self._stream.read()

    def history(self) -> List[str]:
        """Command history newest-last (W11)."""
        return list(self._history)

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

    @property
    def tab_title(self) -> str:
        if self.path is not None:
            mark = "*" if self.dirty else ""
            return f"{mark}{self.path.name}"
        return "*untitled.m" if self.dirty else "untitled.m"


@dataclass
class EditorDocuments:
    """Multi-document Editor group (W10). ``active`` is the focused panel."""

    panels: List[EditorPanel] = field(default_factory=lambda: [EditorPanel()])
    active_index: int = 0

    @property
    def active(self) -> EditorPanel:
        if not self.panels:
            self.panels.append(EditorPanel())
            self.active_index = 0
        if self.active_index < 0 or self.active_index >= len(self.panels):
            self.active_index = 0
        return self.panels[self.active_index]

    def list_titles(self) -> List[str]:
        return [p.tab_title for p in self.panels]

    def new_script(self) -> EditorPanel:
        ed = EditorPanel()
        if (
            len(self.panels) == 1
            and self.panels[0].path is None
            and not self.panels[0].text
            and not self.panels[0].dirty
        ):
            self.panels[0] = ed
            self.active_index = 0
        else:
            self.panels.append(ed)
            self.active_index = len(self.panels) - 1
        return ed

    def open_file(self, path: Path | str) -> EditorPanel:
        p = Path(path).expanduser().resolve()
        for i, ed in enumerate(self.panels):
            if ed.path is not None and ed.path == p:
                self.active_index = i
                return ed
        ed = EditorPanel()
        ed.open_file(p)
        if (
            len(self.panels) == 1
            and self.panels[0].path is None
            and not self.panels[0].text
            and not self.panels[0].dirty
        ):
            self.panels[0] = ed
            self.active_index = 0
        else:
            self.panels.append(ed)
            self.active_index = len(self.panels) - 1
        return ed

    def switch(self, index: int) -> EditorPanel:
        if index < 0 or index >= len(self.panels):
            raise IndexError(f"EditorDocuments.switch: bad index {index}")
        self.active_index = index
        return self.active

    def close_active(self) -> None:
        if len(self.panels) <= 1:
            self.panels = [EditorPanel()]
            self.active_index = 0
            return
        del self.panels[self.active_index]
        if self.active_index >= len(self.panels):
            self.active_index = len(self.panels) - 1


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
                    value=_value_preview(val),
                )
            )
        return out

    def refresh(self) -> List[WorkspaceRow]:
        return self.rows()

    def as_table(self) -> str:
        lines = [f"{'Name':<16} {'Value':<20} {'Size':<12} Class"]
        lines.append("-" * 60)
        for r in self.rows():
            lines.append(f"{r.name:<16} {r.value:<20} {r.size:<12} {r.matlab_class}")
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
    documents: EditorDocuments
    workspace_browser: WorkspaceBrowser
    current_folder: CurrentFolderBrowser
    figures: FigureManager
    plugin_paths: List[Path] = field(default_factory=list)
    layout_preset: str = "default"
    _plugin_host: Any = None

    @property
    def editor(self) -> EditorPanel:
        """Active Editor document (W03/W10)."""
        return self.documents.active

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
            documents=EditorDocuments(),
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

    def menu_bar(self) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
        """Menu bar spec (W07)."""
        return MENU_BAR_SPEC

    def toolbar(self) -> Tuple[str, ...]:
        """Toolstrip / toolbar actions (W08)."""
        return TOOLBAR_SPEC

    def dock_layout(self) -> dict:
        """Classic dock positions for chrome + host regions (W09)."""
        return dict(DEFAULT_DOCK)

    def apply_layout_preset(self, name: str = "default") -> str:
        """Apply a named layout preset (W15 MVP — default only)."""
        key = (name or "default").strip().lower()
        if key not in LAYOUT_PRESETS:
            raise ValueError(f"Unknown layout preset: {name!r} (known: {LAYOUT_PRESETS})")
        self.layout_preset = key
        return key

    def regions(self) -> List[RegionSpec]:
        """Host layout regions + any discovered plugin panels."""
        specs = [
            RegionSpec(
                "command_window",
                "Command Window",
                "host",
                "ready",
                "ReplSession eval + history (W02/W11)",
            ),
            RegionSpec(
                "editor",
                "Editor",
                "host",
                "ready",
                "multi-doc open/edit/save .m (W03/W10)",
            ),
            RegionSpec(
                "workspace_browser",
                "Workspace",
                "host",
                "ready",
                "name/value/size/class (W04/W12)",
            ),
            RegionSpec(
                "current_folder",
                "Current Folder",
                "host",
                "ready",
                "list/cd/path toolbar (W05/W13)",
            ),
            RegionSpec(
                "figures",
                "Figures",
                "host",
                "ready",
                "docked list/close/focus (W06/W14)",
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
        dock = self.dock_layout()
        lines = [f"{'ID':<28} {'TITLE':<18} {'KIND':<8} {'DOCK':<8} STATUS"]
        lines.append("-" * 80)
        for r in self.regions():
            slot = dock.get(r.id, "-")
            lines.append(f"{r.id:<28} {r.title:<18} {r.kind:<8} {slot:<8} {r.status}")
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
        """MATLAB Desktop–aligned tk chrome: menu, toolstrip, path bar, classic docks."""
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk

        if self.plugin_paths and self._plugin_host is None:
            self._ensure_plugins(activate=True)

        root = tk.Tk()
        root.title(title)
        root.geometry("1280x800")

        # --- Menu bar (W07) ---
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        menus: dict = {}
        for menu_label, items in self.menu_bar():
            m = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label=menu_label, menu=m)
            menus[menu_label] = m
            for item in items:
                m.add_command(label=item)

        # --- Toolstrip (W08) ---
        tool = ttk.Frame(root, padding=(6, 4))
        tool.pack(fill="x")
        ttk.Label(tool, text="Home", font=("", 10, "bold")).pack(side="left", padx=(0, 8))
        tool_btns: dict = {}
        for label in self.toolbar():
            b = ttk.Button(tool, text=label)
            b.pack(side="left", padx=2)
            tool_btns[label] = b

        # --- Current Folder path toolbar (W13) ---
        path_bar = ttk.Frame(root, padding=(6, 2))
        path_bar.pack(fill="x")
        ttk.Label(path_bar, text="Current Folder:").pack(side="left")
        path_var = tk.StringVar(value=str(self.current_folder.pwd()))
        path_entry = ttk.Entry(path_bar, textvariable=path_var)
        path_entry.pack(side="left", fill="x", expand=True, padx=4)
        path_up_btn = ttk.Button(path_bar, text="Up", width=4)
        path_up_btn.pack(side="left")

        # --- Classic docked body (W09): CF | Editor+CW | WS+Figures ---
        body = ttk.Panedwindow(root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=4, pady=4)

        left = ttk.Frame(body, padding=2)
        center = ttk.Frame(body, padding=2)
        right = ttk.Frame(body, padding=2)
        body.add(left, weight=1)
        body.add(center, weight=4)
        body.add(right, weight=2)

        # Current Folder (left)
        ttk.Label(left, text="Current Folder", font=("", 10, "bold")).pack(anchor="w")
        cf_list = tk.Listbox(left, height=28)
        cf_list.pack(fill="both", expand=True)

        # Center: Editor tabs (top) + Command Window (bottom)
        center_split = ttk.Panedwindow(center, orient="vertical")
        center_split.pack(fill="both", expand=True)
        ed_frame = ttk.Frame(center_split, padding=2)
        cw_frame = ttk.Frame(center_split, padding=2)
        center_split.add(ed_frame, weight=3)
        center_split.add(cw_frame, weight=2)

        ttk.Label(ed_frame, text="Editor", font=("", 10, "bold")).pack(anchor="w")
        ed_nb = ttk.Notebook(ed_frame)
        ed_nb.pack(fill="both", expand=True)
        ed_text_widgets: list = []

        ttk.Label(cw_frame, text="Command Window", font=("", 10, "bold")).pack(anchor="w")
        out = tk.Text(cw_frame, height=10, wrap="word", font=("Courier", 10))
        out.pack(fill="both", expand=True)
        cw_row = ttk.Frame(cw_frame)
        cw_row.pack(fill="x", pady=2)
        ttk.Label(cw_row, text=">>").pack(side="left")
        entry = ttk.Entry(cw_row, font=("Courier", 10))
        entry.pack(side="left", fill="x", expand=True, padx=4)
        hist_index = {"i": 0}

        # Right: Workspace + docked Figures (W14)
        right_split = ttk.Panedwindow(right, orient="vertical")
        right_split.pack(fill="both", expand=True)
        ws_frame = ttk.Frame(right_split, padding=2)
        fig_frame = ttk.Frame(right_split, padding=2)
        right_split.add(ws_frame, weight=2)
        right_split.add(fig_frame, weight=1)

        ttk.Label(ws_frame, text="Workspace", font=("", 10, "bold")).pack(anchor="w")
        ws_tree = ttk.Treeview(
            ws_frame, columns=("value", "size", "class"), show="tree headings", height=12
        )
        ws_tree.heading("#0", text="Name")
        ws_tree.heading("value", text="Value")
        ws_tree.heading("size", text="Size")
        ws_tree.heading("class", text="Class")
        ws_tree.column("#0", width=90)
        ws_tree.column("value", width=110)
        ws_tree.column("size", width=60)
        ws_tree.column("class", width=60)
        ws_tree.pack(fill="both", expand=True)

        ttk.Label(fig_frame, text="Figures", font=("", 10, "bold")).pack(anchor="w")
        fig_list = tk.Listbox(fig_frame, height=8)
        fig_list.pack(fill="both", expand=True)
        fig_btns = ttk.Frame(fig_frame)
        fig_btns.pack(fill="x", pady=2)

        def _active_ed_text():
            if not ed_text_widgets:
                return None
            i = self.documents.active_index
            if i < 0 or i >= len(ed_text_widgets):
                i = 0
            return ed_text_widgets[i]

        def _sync_editor_from_ui() -> None:
            w = _active_ed_text()
            if w is None:
                return
            self.editor.set_text(w.get("1.0", "end-1c"))

        def _rebuild_editor_tabs() -> None:
            for tab_id in ed_nb.tabs():
                ed_nb.forget(tab_id)
            ed_text_widgets.clear()
            for i, panel in enumerate(self.documents.panels):
                tab = ttk.Frame(ed_nb)
                ed_nb.add(tab, text=panel.tab_title)
                txt = tk.Text(tab, wrap="none", font=("Courier", 10))
                txt.pack(fill="both", expand=True)
                txt.insert("1.0", panel.text)
                ed_text_widgets.append(txt)
            if self.documents.panels:
                ed_nb.select(self.documents.active_index)

        def _on_ed_tab_changed(_event=None) -> None:
            try:
                idx = ed_nb.index(ed_nb.select())
            except tk.TclError:
                return
            if 0 <= idx < len(self.documents.panels):
                # flush previous active first
                prev = self.documents.active_index
                if 0 <= prev < len(ed_text_widgets):
                    self.documents.panels[prev].set_text(
                        ed_text_widgets[prev].get("1.0", "end-1c")
                    )
                self.documents.switch(idx)

        ed_nb.bind("<<NotebookTabChanged>>", _on_ed_tab_changed)

        def refresh_cf() -> None:
            path_var.set(str(self.current_folder.pwd()))
            cf_list.delete(0, "end")
            for e in self.current_folder.list_entries():
                mark = "[dir] " if e.kind == "dir" else ("[m]   " if e.is_mfile else "      ")
                cf_list.insert("end", f"{mark}{e.name}")

        def refresh_ws() -> None:
            ws_tree.delete(*ws_tree.get_children())
            for row in self.workspace_browser.refresh():
                ws_tree.insert(
                    "",
                    "end",
                    text=row.name,
                    values=(row.value, row.size, row.matlab_class),
                )

        def refresh_figs() -> None:
            fig_list.delete(0, "end")
            for info in self.figures.list_figures():
                fig_list.insert("end", f"{info.handle:g}  {info.title}")

        def path_go(_event=None) -> None:
            target = path_var.get().strip()
            if not target:
                return
            try:
                self.current_folder.cd(target)
                refresh_cf()
            except Exception as exc:
                messagebox.showerror("Current Folder", str(exc))
                path_var.set(str(self.current_folder.pwd()))

        def path_up() -> None:
            try:
                self.current_folder.cd("..")
                refresh_cf()
            except Exception as exc:
                messagebox.showerror("Current Folder", str(exc))

        path_entry.bind("<Return>", path_go)
        path_up_btn.configure(command=path_up)

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
                self.documents.open_file(self.current_folder.pwd() / name)
                _rebuild_editor_tabs()

        cf_list.bind("<Double-Button-1>", cf_open_selected)

        def ed_new() -> None:
            _sync_editor_from_ui()
            self.documents.new_script()
            _rebuild_editor_tabs()

        def ed_open() -> None:
            path = filedialog.askopenfilename(
                title="Open .m file",
                filetypes=[("MATLAB files", "*.m"), ("All", "*.*")],
                initialdir=str(self.current_folder.pwd()),
            )
            if not path:
                return
            _sync_editor_from_ui()
            self.documents.open_file(path)
            _rebuild_editor_tabs()

        def ed_save() -> None:
            _sync_editor_from_ui()
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
                _rebuild_editor_tabs()
            except Exception as exc:
                messagebox.showerror("Editor", str(exc))

        def ed_close() -> None:
            _sync_editor_from_ui()
            self.documents.close_active()
            _rebuild_editor_tabs()

        def ed_run() -> None:
            _sync_editor_from_ui()
            src = self.editor.text.strip()
            if not src:
                return
            out.insert("end", f">> (run editor)\n")
            try:
                text = self.command_window.eval(src)
                if text:
                    out.insert("end", text)
            except Exception as exc:
                out.insert("end", f"Error: {exc}\n")
            out.see("end")
            refresh_ws()
            refresh_figs()

        def on_eval(_event=None) -> None:
            line = entry.get().strip()
            if not line:
                return
            entry.delete(0, "end")
            hist_index["i"] = 0
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

        def hist_up(_event=None):
            hist = self.command_window.history()
            if not hist:
                return "break"
            hist_index["i"] = min(hist_index["i"] + 1, len(hist))
            entry.delete(0, "end")
            entry.insert(0, hist[-hist_index["i"]])
            return "break"

        def hist_down(_event=None):
            hist = self.command_window.history()
            if hist_index["i"] <= 1:
                hist_index["i"] = 0
                entry.delete(0, "end")
                return "break"
            hist_index["i"] -= 1
            entry.delete(0, "end")
            entry.insert(0, hist[-hist_index["i"]])
            return "break"

        entry.bind("<Return>", on_eval)
        entry.bind("<Up>", hist_up)
        entry.bind("<Down>", hist_down)

        def _selected_handle():
            sel = fig_list.curselection()
            if not sel:
                return None
            return float(fig_list.get(sel[0]).split()[0])

        def fig_close() -> None:
            self.figures.close(_selected_handle())
            refresh_figs()

        def fig_focus() -> None:
            h = _selected_handle()
            if h is None:
                return
            try:
                self.figures.focus(h)
            except Exception as exc:
                messagebox.showerror("Figures", str(exc))

        ttk.Button(fig_btns, text="Refresh", command=refresh_figs).pack(side="left", padx=2)
        ttk.Button(fig_btns, text="Close", command=fig_close).pack(side="left", padx=2)
        ttk.Button(fig_btns, text="Focus", command=fig_focus).pack(side="left", padx=2)

        # Wire menu + toolbar
        def do_exit() -> None:
            root.destroy()

        def layout_default() -> None:
            self.apply_layout_preset("default")
            messagebox.showinfo("Layout", "Default desktop layout applied.")

        menus["File"].entryconfigure("New Script", command=ed_new)
        menus["File"].entryconfigure("Open…", command=ed_open)
        menus["File"].entryconfigure("Save", command=ed_save)
        menus["File"].entryconfigure("Close Document", command=ed_close)
        menus["File"].entryconfigure("Exit", command=do_exit)
        menus["Layout"].entryconfigure("Default", command=layout_default)
        tool_btns["New Script"].configure(command=ed_new)
        tool_btns["Open…"].configure(command=ed_open)
        tool_btns["Save"].configure(command=ed_save)
        tool_btns["Run"].configure(command=ed_run)

        _rebuild_editor_tabs()
        refresh_cf()
        refresh_ws()
        refresh_figs()

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
            sample = self.current_folder.pwd() / "showcase_demo.m"
            if not sample.is_file():
                sample.parent.mkdir(parents=True, exist_ok=True)
                sample.write_text(
                    "% showcase demo\nx = 1:5;\ny = x .* x;\n", encoding="utf-8"
                )
                refresh_cf()
            sample2 = self.current_folder.pwd() / "notes_helper.m"
            if not sample2.is_file():
                sample2.write_text("% second doc\nz = 9;\n", encoding="utf-8")
                refresh_cf()

            root.after(500, lambda: _demo_eval("a = [1 2 3 4];"))
            root.after(1200, lambda: _demo_eval("b = a .* 2"))
            root.after(
                2000,
                lambda: (
                    self.documents.open_file(sample),
                    _rebuild_editor_tabs(),
                ),
            )
            root.after(
                3200,
                lambda: (
                    self.documents.open_file(sample2),
                    _rebuild_editor_tabs(),
                ),
            )
            root.after(4200, lambda: _demo_eval("plot(1:8);"))
            root.after(5200, lambda: _demo_eval("plot(1:4);"))
            root.after(6000, refresh_figs)
            root.after(6500, refresh_cf)

        if demo_ms is not None and demo_ms > 0:
            root.after(200, _schedule_demo)
            root.after(int(demo_ms), root.destroy)
        root.mainloop()
