# Epic #702 (D-E5): Variable editor panel

Milestone: [M11 Debugger and Workbench](../milestones/M11-debugger-workbench.md), criterion D09.

## Design

- **Model.** `host/variable_editor.py` `VariableEditor` is the Host-owned Variables region. `open(name)` returns a `VariableView` over the variable in the *shown* workspace: the selected debug frame while paused, otherwise base (the same source as the Workspace browser). Views are read live, so an edit at the Command Window shows on the next refresh.
- **Kinds.** numeric/logical (N-D folded to rows × prod(rest), as MATLAB shows pages side by side), char (one character per cell), string, cell (element summaries, e.g. `'x'`, `[1 2 3]`, `1×2 cell`), scalar struct (Field | Value rows), table (one column per variable, row names as row headers). Struct arrays and objects open read-only.
- **Shape.** `size()` returns the grid shape as a MATLAB 1×2 row vector; `rc()` returns it as a `(rows, cols)` tuple.
- **Write-back.** `set_cell(r, c, text)` evaluates `text` as a single MATLAB expression in the shown workspace and assigns with MATLAB semantics: `A(r,c) = v` (grows with zero fill, as indexed assignment does), `C{r,c} = v`, `s.(field) = v`, `T{r,c} = v`. A typed single character in a char variable is that character. Edits do not enter the Command History.
- **Errors.** A bad edit raises `VariableEditError` with MATLAB-style text and leaves the variable unchanged; the tk tab shows the message in its status line. No Python traceback reaches the user.
- **tk chrome.** A Variables notebook sits between the Editor and the Command Window; double-click or Enter on a Workspace row opens a tab, double-click a cell to edit, Enter commits, Escape cancels. Tabs close when their variable leaves the shown workspace.
