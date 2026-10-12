# Design: MATLAB-aligned Workbench (Epic #372)

## Approach

Host-owned `Workbench` with five named regions **plus** Desktop chrome
(menu bar, toolstrip, path toolbar, classic docks). Plugins contribute
additional panels via the extensions `panels` slot; they never fork this
shell (PLUGIN-CONTRACT).

### Panel MVP (W01–W06) — met

| Criterion | Panel | API surface |
|-----------|-------|-------------|
| W01 | Layout registry | `HOST_REGIONS`, `Workbench.regions()` |
| W02 | Command Window | `CommandWindow.eval` / `ReplSession` + display capture |
| W03 | Editor | `EditorPanel.open_file` / `set_text` / `save` (`.m` MVP) |
| W04 | Workspace | `WorkspaceBrowser.rows` — name / size / class |
| W05 | Current Folder | `CurrentFolderBrowser.pwd` / `cd` / `list_entries` / `open_mfile` |
| W06 | Figures | `FigureManager.list_figures` / `close` / `focus` via `PlotSurface` |

### Layout parity (W07–W15)

| Criterion | Chrome | API / UI surface |
|-----------|--------|------------------|
| W07 | Menu bar | `MENU_BAR_SPEC`, `Workbench.menu_bar()`, tk `Menu` |
| W08 | Toolstrip | `TOOLBAR_SPEC`, `Workbench.toolbar()`, Home buttons |
| W09 | Classic docks | `DEFAULT_DOCK`, `Workbench.dock_layout()` — CF left, Editor center, CW bottom, WS+Figs right |
| W10 | Multi-doc Editor | `EditorDocuments` (active = `workbench.editor`) |
| W11 | CW history | `CommandWindow.history()`, tk ↑/↓ |
| W12 | Workspace Value | `WorkspaceRow.value` |
| W13 | Path toolbar | editable path + Up under toolstrip |
| W14 | Docked Figures | Figures pane in right dock (not notebook-only) |
| W15 | Layout presets | `LAYOUT_PRESETS`, `apply_layout_preset("default")` |

CLI: `openmatlab workbench --list-only` (shows DOCK column) / `--eval CODE` /
tk surface (`--demo-ms` for recordings).

Non-goals: LSP/debugger, browser workbench, marketplace, pixel-perfect ribbon.
