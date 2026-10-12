# Design: MATLAB-aligned Workbench (Epic #372)

## Approach

Host-owned `Workbench` with five named regions. Plugins contribute additional
panels via the extensions `panels` slot; they never fork this shell
(PLUGIN-CONTRACT).

| Criterion | Panel | API surface |
|-----------|-------|-------------|
| W01 | Layout registry | `HOST_REGIONS`, `Workbench.regions()` |
| W02 | Command Window | `CommandWindow.eval` / `ReplSession` + display capture |
| W03 | Editor | `EditorPanel.open_file` / `set_text` / `save` (`.m` MVP) |
| W04 | Workspace | `WorkspaceBrowser.rows` — name / size / class |
| W05 | Current Folder | `CurrentFolderBrowser.pwd` / `cd` / `list_entries` / `open_mfile` |
| W06 | Figures | `FigureManager.list_figures` / `close` / `focus` via `PlotSurface` |

CLI: `openmatlab workbench --list-only` / `--eval CODE` / tk surface
(`--demo-ms` for recordings).

Non-goals: LSP/debugger, browser workbench, marketplace.
