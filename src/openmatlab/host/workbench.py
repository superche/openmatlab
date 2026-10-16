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

    @property
    def name(self) -> str:
        """Region title as shown in the Desktop (alias used by tooling)."""
        return self.title


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

    _last_error: Optional[Tuple[str, int]] = None  # (file, line) of the last uncaught error (M11 D-E6)

    def eval(self, source: str, *, history: bool = True) -> str:
        """Evaluate one or more statements; return captured display text.

        Raises the evaluation error (callers decide how to show it); the error's location is
        recorded for the Command Window error hyperlink (``last_error_location``).
        """
        line = source.strip()
        if line and history:
            self._history.append(line)
        before = self._stream.tell()
        try:
            self.repl.run_line(source)
        except Exception as exc:
            self.record_error(exc)
            raise
        self._stream.seek(before)
        return self._stream.read()

    def record_error(self, exc) -> None:
        frames = [f for f in (getattr(exc, "mstack", None) or ()) if f and f[0]]
        self._last_error = (str(frames[0][0]), int(frames[0][2])) if frames else None

    def error_text(self, exc) -> str:
        """MATLAB-style uncaught error text ("Error using f (line n)" + message); never a traceback."""
        from openmatlab.runtime import errors

        frames = tuple(getattr(exc, "mstack", None) or ())
        return errors.report(str(exc), frames, basic=True) if frames else f"Error: {exc}"

    def last_error_location(self) -> Optional[Tuple[str, int]]:
        """``(file, line)`` the last error's hyperlink points to, or ``None`` (M11 D-E6)."""
        return self._last_error

    def rerun_history(self, index: int = -1) -> str:
        """Command History re-run: evaluate entry ``index`` (Python-style; -1 = newest) again."""
        hist = self._history
        if not hist:
            raise IndexError("Command History is empty")
        return self.eval(hist[index])

    def history(self) -> List[str]:
        """Command history newest-last (W11)."""
        return list(self._history)

    def workspace_names(self) -> List[str]:
        return sorted(n for n in self.session.workspace.names() if n != "ans")


def _is_section_marker(line: str) -> bool:
    t = line.lstrip()
    return t.startswith("%%") and (len(t) == 2 or t[2] in " \t")


class _Title(str):
    """Tab title string; also callable (``ed.tab_title()``) for tooling."""

    def __call__(self) -> str:
        return str(self)


@dataclass
class EditorPanel:
    """Editor MVP — open / edit / save ``.m`` files (W03)."""

    path: Optional[Path] = None
    text: str = ""
    dirty: bool = False
    session: Any = field(default=None, repr=False, compare=False)  # set by EditorDocuments (D-E4)
    _cursor: int = 1  # 1-based caret line (M11 D-E6)

    # -- code sections (M11 D-E6) ------------------------------------------------
    def sections(self) -> List[Tuple[int, int]]:
        """Code sections as 1-based inclusive ``(first, last)`` line ranges.

        A line whose first non-blank characters are ``%%`` followed by a space or the end of the
        line starts a section (MATLAB); text before the first marker is a section of its own.
        """
        lines = self.text.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        starts = [i + 1 for i, ln in enumerate(lines) if _is_section_marker(ln)]
        if not lines:
            return [(1, 1)]
        if not starts or starts[0] != 1:
            starts = [1] + starts
        ends = [b - 1 for b in starts[1:]] + [len(lines)]
        return list(zip(starts, ends))

    def section_at(self, line: Optional[int] = None) -> Tuple[int, int]:
        ln = self._cursor if line is None else line
        secs = self.sections()
        for a, b in secs:
            if a <= ln <= b:
                return (a, b)
        return secs[-1]

    def section_text(self, line: Optional[int] = None) -> str:
        a, b = self.section_at(line)
        return "\n".join(self.text.split("\n")[a - 1:b])

    def set_cursor_line(self, line: int) -> None:
        n = max(1, len(self.text.split("\n")))
        self._cursor = min(max(1, int(line)), n)

    def cursor_line(self) -> int:
        return self._cursor

    def toggle_breakpoint(self, line: int) -> None:
        """Gutter click at ``line``: dbstop / dbclear on the saved file (M11 D-E4)."""
        from openmatlab.host import debug_ui

        if self.path is None or self.session is None:
            raise ValueError("Editor.toggle_breakpoint: save the document to a file first")
        debug_ui.toggle_breakpoint(self.session, self.path, line)

    def breakpoints(self):
        """Gutter breakpoint lines (shared with dbstatus): 1×N row vector, 0×0 when none."""
        import numpy as np

        from openmatlab.host import debug_ui

        if self.path is None or self.session is None:
            return np.zeros((0, 0), dtype=int)
        return debug_ui.breakpoints(self.session, self.path)

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
            return _Title(f"{mark}{self.path.name}")
        return _Title("*untitled.m" if self.dirty else "untitled.m")


@dataclass
class EditorDocuments:
    """Multi-document Editor group (W10). ``active`` is the focused panel."""

    panels: List[EditorPanel] = field(default_factory=lambda: [EditorPanel()])
    active_index: int = 0
    session: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        for ed in self.panels:
            self._bind(ed)

    def _bind(self, ed: EditorPanel) -> EditorPanel:
        ed.session = self.session
        return ed

    @property
    def active(self) -> EditorPanel:
        if not self.panels:
            self.panels.append(self._bind(EditorPanel()))
            self.active_index = 0
        if self.active_index < 0 or self.active_index >= len(self.panels):
            self.active_index = 0
        return self.panels[self.active_index]

    def list_titles(self) -> List[str]:
        return [p.tab_title for p in self.panels]

    def new_script(self) -> EditorPanel:
        ed = self._bind(EditorPanel())
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
        ed = self._bind(EditorPanel())
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
            self.panels = [self._bind(EditorPanel())]
            self.active_index = 0
            return
        del self.panels[self.active_index]
        if self.active_index >= len(self.panels):
            self.active_index = len(self.panels) - 1


@dataclass
class WorkspaceBrowser:
    """Workspace browser — name/size/class + refresh (W04)."""

    session: Session
    source: Any = field(default=None, repr=False, compare=False)  # () -> workspace (debug stack selector)

    def _ws(self):
        return self.source() if self.source is not None else self.session.workspace

    def names(self) -> List[str]:
        return sorted(n for n in self._ws().names() if n != "ans")

    def rows(self) -> List[WorkspaceRow]:
        out: List[WorkspaceRow] = []
        ws = self._ws()
        for name in sorted(n for n in ws.names() if n != "ans"):
            val = ws.get(name)
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
    debug: Any = None  # DebugController (M11 D-E4)
    variable_editor: Any = None  # VariableEditor (M11 D-E5)

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
        from openmatlab.host.debug_ui import DebugController

        debug = DebugController(cw)
        wb = cls(
            command_window=cw,
            documents=EditorDocuments(session=cw.session),
            workspace_browser=WorkspaceBrowser(session=cw.session, source=debug.active_workspace),
            current_folder=CurrentFolderBrowser.create(cwd=cwd),
            figures=FigureManager(session=cw.session),
            plugin_paths=paths,
            debug=debug,
        )
        from openmatlab.host.variable_editor import VariableEditor

        wb.variable_editor = VariableEditor(workspace_source=wb.workspace_browser._ws,
                                            functions_source=lambda: cw.session)
        if cwd is not None:  # the Current Folder is on the search path (MATLAB)
            cw.session.path.addpath(wb.current_folder.pwd())
        if activate_plugins and paths:
            wb._ensure_plugins(activate=True)
        return wb

    def eval(self, source: str) -> str:
        """Command Window eval; workspace browser reflects side effects.

        While the debugger is paused the line goes to the ``K>>`` prompt instead.
        """
        cw = self.command_window
        if self.debug is not None and self.debug.is_paused():
            before = cw._stream.tell()
            cw._history.append(source.strip())
            self.debug.send(source)
            cw._stream.seek(before)
            return cw._stream.read()
        before = cw._stream.tell()
        try:
            return cw.eval(source)
        except Exception as exc:  # shown in the Command Window as MATLAB error text, never a traceback
            cw._stream.seek(0, 2)
            cw._stream.write(cw.error_text(exc) + "\n")
            cw._stream.seek(before)
            return cw._stream.read()

    # -- Workbench workflows (M11 D-E6) --------------------------------------------
    def _run_code(self, source: str) -> None:
        """Run editor code through the debug controller (breakpoints apply); no Command History entry."""
        self.debug.run(source, history=False)

    def run_section(self) -> None:
        """Run Section: evaluate the section at the caret in the base workspace."""
        self._run_code(self.editor.section_text())

    def run_and_advance(self) -> None:
        """Run and Advance: run the caret's section, then move the caret to the next section."""
        ed = self.editor
        a, b = ed.section_at()
        self._run_code(ed.section_text())
        nxt = [s for s in ed.sections() if s[0] > b]
        if nxt:
            ed.set_cursor_line(nxt[0][0])

    def run_file(self) -> None:
        """Editor Run: save if needed and run the file so its breakpoints apply."""
        ed = self.editor
        if ed.path is None:
            self._run_code(ed.text)
            return
        if ed.dirty:
            ed.save()
        p = ed.path.as_posix().replace("'", "''")
        self._run_code(f"run('{p}')")

    def open_error_link(self) -> Optional[EditorPanel]:
        """Follow the last error's hyperlink: open its file in the Editor at the error line."""
        loc = self.command_window.last_error_location()
        if loc is None or not Path(loc[0]).is_file():
            return None
        ed = self.documents.open_file(loc[0])
        ed.set_cursor_line(loc[1])
        return ed

    @property
    def workspace(self) -> "WorkspaceBrowser":
        """Workspace panel; while paused it shows the frame picked in the stack selector."""
        return self.workspace_browser

    def eval_value(self, name: str):
        """Value of a variable in the shown workspace as a Python scalar / nested list (tests, tooling)."""
        import numpy as np

        ws = self.workspace_browser._ws()
        if name in ws.names():
            v = ws.get(name)
        else:  # an expression such as A(2,1), c{1}, s.f, T.x(1), evaluated in the shown workspace (M11 D-E5)
            ve = self.variable_editor
            v = ve._with_ev(lambda ev: ve._parse_value(ev, name))
        text = getattr(v, "text", None)
        if isinstance(text, str):
            return text
        a = np.asarray(v.backend_buffer())
        return a.reshape(-1)[0].item() if a.size == 1 else a.tolist()

    def debug_toolbar(self) -> Tuple[str, ...]:
        """Editor debug toolbar actions (M11 D-E4)."""
        from openmatlab.host.debug_ui import DEBUG_TOOLBAR

        return DEBUG_TOOLBAR

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
                "variables",
                "Variables",
                "host",
                "ready",
                "variable editor: numeric/char/cell/struct/table, edit writes back (M11 D-E5)",
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
        var_frame = ttk.Frame(center_split, padding=2)  # Variables editor (M11 D-E5)
        center_split.add(ed_frame, weight=3)
        center_split.add(var_frame, weight=1)
        center_split.add(cw_frame, weight=2)
        ttk.Label(var_frame, text="Variables", font=("", 10, "bold")).pack(anchor="w")
        var_nb = ttk.Notebook(var_frame)
        var_nb.pack(fill="both", expand=True)
        var_tabs: dict = {}

        ttk.Label(ed_frame, text="Editor", font=("", 10, "bold")).pack(anchor="w")
        # Debug toolbar + stack selector (M11 D-E4); F12 or a gutter click toggles a breakpoint
        dbg_bar = ttk.Frame(ed_frame)
        dbg_bar.pack(fill="x", pady=(0, 2))
        dbg_btns: dict = {}
        for label in self.debug_toolbar():
            b = ttk.Button(dbg_bar, text=label, state="disabled")
            b.pack(side="left", padx=1)
            dbg_btns[label] = b
        ttk.Label(dbg_bar, text="  Stack:").pack(side="left")
        stack_var = tk.StringVar(value="")
        stack_box = ttk.Combobox(dbg_bar, textvariable=stack_var, state="disabled", width=36)
        stack_box.pack(side="left", padx=2)
        ed_nb = ttk.Notebook(ed_frame)
        ed_nb.pack(fill="both", expand=True)
        ed_text_widgets: list = []

        ttk.Label(cw_frame, text="Command Window", font=("", 10, "bold")).pack(anchor="w")
        out = tk.Text(cw_frame, height=10, wrap="word", font=("Courier", 10))
        out.pack(fill="both", expand=True)
        cw_row = ttk.Frame(cw_frame)
        cw_row.pack(fill="x", pady=2)
        prompt_var = tk.StringVar(value=">>")
        ttk.Label(cw_row, textvariable=prompt_var).pack(side="left")
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
                ed_nb.nametowidget(tab_id).destroy()
            ed_text_widgets.clear()
            for i, panel in enumerate(self.documents.panels):
                tab = ttk.Frame(ed_nb)
                ed_nb.add(tab, text=panel.tab_title)
                gutter = tk.Text(tab, width=6, wrap="none", font=("Courier", 10), cursor="hand2",
                                 background="#f0f0f0", borderwidth=0)
                gutter.pack(side="left", fill="y")
                txt = tk.Text(tab, wrap="none", font=("Courier", 10))
                txt.pack(side="left", fill="both", expand=True)
                txt.insert("1.0", panel.text)
                txt.tag_configure("bp", background="#f6d0d0")
                txt.tag_configure("cur", background="#fff2a8")
                txt.bind("<F12>", lambda _e, w=txt: _toggle_bp(int(w.index("insert").split(".")[0])))
                gutter.bind("<Button-1>", lambda e, g=gutter: (
                    _toggle_bp(int(g.index(f"@{e.x},{e.y}").split(".")[0])), "break")[1])
                txt.gutter = gutter
                ed_text_widgets.append(txt)
            if self.documents.panels:
                ed_nb.select(self.documents.active_index)
            _paint_debug()

        def _paint_debug() -> None:
            """Gutter breakpoint dots, current-line marker, toolbar state, stack selector."""
            for panel, txt in zip(self.documents.panels, ed_text_widgets):
                n = int(txt.index("end-1c").split(".")[0])
                bps = set(int(x) for x in panel.breakpoints().reshape(-1)) if panel.path else set()
                g = txt.gutter
                g.configure(state="normal")
                g.delete("1.0", "end")
                g.insert("1.0", "\n".join(("\u25cf" if k in bps else " ") + f"{k:>4}" for k in range(1, n + 1)))
                g.configure(state="disabled")
                txt.tag_remove("bp", "1.0", "end")
                txt.tag_remove("cur", "1.0", "end")
                for k in bps:
                    txt.tag_add("bp", f"{k}.0", f"{k}.end+1c")
                cf = self.debug.current_file()
                if cf is not None and panel.path == cf:
                    ln = self.debug.current_line()
                    txt.tag_add("cur", f"{ln}.0", f"{ln}.end+1c")
                    txt.see(f"{ln}.0")
            paused = self.debug.is_paused()
            for b in dbg_btns.values():
                b.configure(state="normal" if paused else "disabled")
            frames = self.debug.stack()
            stack_box.configure(values=[f"{n} (line {ln})" for n, _f, ln in frames],
                                state="readonly" if paused else "disabled")
            stack_var.set(stack_box["values"][self.debug.selected_frame()] if frames else "")
            prompt_var.set("K>>" if paused else ">>")

        def _show_paused() -> None:
            text = self.command_window._stream.getvalue()[_out_mark["n"]:]
            _out_mark["n"] = len(self.command_window._stream.getvalue())
            if text:
                out.insert("end", text)
                out.see("end")
            cf = self.debug.current_file()
            if cf is not None and cf.is_file():
                self.documents.open_file(cf)
                _rebuild_editor_tabs()
            else:
                _paint_debug()
            refresh_ws()
            refresh_figs()

        _out_mark = {"n": 0}

        def _toggle_bp(line: int) -> None:
            _sync_editor_from_ui()
            try:
                if self.editor.dirty:
                    self.editor.save()
                self.editor.toggle_breakpoint(line)
            except Exception as exc:
                messagebox.showerror("Breakpoints", str(exc))
            _paint_debug()

        def _debug_action(fn) -> None:
            try:
                fn()
            except Exception as exc:
                out.insert("end", f"Error: {exc}\n")
            _show_paused()

        def _on_stack(_event=None) -> None:
            vals = list(stack_box["values"])
            if stack_var.get() in vals:
                self.debug.select_frame(vals.index(stack_var.get()))
                _show_paused()

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

        def refresh_vars() -> None:
            names = set(self.workspace_browser.names())
            for nm in list(var_tabs):
                if nm not in names:  # cleared, or not in the selected frame
                    var_nb.forget(var_tabs.pop(nm))
                    self.variable_editor.close(nm)
                else:
                    var_tabs[nm].refresh()

        def open_variable(name: str) -> None:
            from openmatlab.host.variable_editor import VariableEditError, open_tk

            try:
                view = self.variable_editor.open(name)
            except VariableEditError as exc:
                messagebox.showerror("Variables", str(exc))
                return
            if name not in var_tabs:
                var_tabs[name] = open_tk(var_nb, view, on_written=refresh_ws)
                var_nb.add(var_tabs[name], text=name)
            var_nb.select(var_tabs[name])

        def _ws_open(_event=None) -> None:
            sel = ws_tree.focus()
            if sel:
                open_variable(ws_tree.item(sel, "text"))

        ws_tree.bind("<Double-1>", _ws_open)
        ws_tree.bind("<Return>", _ws_open)

        def refresh_ws() -> None:
            refresh_vars()
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
            out.insert("end", ">> (run editor)\n")
            _out_mark["n"] = len(self.command_window._stream.getvalue())
            if self.editor.path is not None:  # run the saved file so its breakpoints apply
                if self.editor.dirty:
                    self.editor.save()
                p = self.editor.path.as_posix().replace("'", "''")
                _debug_action(lambda: self.debug.run(f"run('{p}')"))
            else:
                _debug_action(lambda: self.debug.run(src))

        def on_eval(_event=None) -> None:
            line = entry.get().strip()
            if not line:
                return
            entry.delete(0, "end")
            hist_index["i"] = 0
            out.insert("end", f"{prompt_var.get()} {line}\n")
            _out_mark["n"] = len(self.command_window._stream.getvalue())
            if self.debug.is_paused():
                self.command_window._history.append(line)
                _debug_action(lambda: self.debug.send(line))
            else:
                _debug_action(lambda: self.debug.run(line))

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
        for label, fn in zip(self.debug_toolbar(), (self.debug.continue_, self.debug.step, self.debug.step_in,
                                                    self.debug.step_out, self.debug.quit)):
            dbg_btns[label].configure(command=lambda f=fn: _debug_action(f))
        stack_box.bind("<<ComboboxSelected>>", _on_stack)

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
