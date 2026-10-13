# Design: Epic #537, graphics core (M7 C08)

Covers #557 (handle model, get/set, gca/gcf, close, saveas), #558 (hold, subplot, title/xlabel/ylabel, legend, grid, axis, xlim/ylim) and #559 (bar, scatter, histogram).

## First principles
- **The model is the source of truth.** `graphics/handle_model.py` keeps the MATLAB object tree: root `0` → figures → axes → line/bar/scatter/histogram/text, plus legends. Every change re-renders the affected figure through the session's GraphicsBackend (`render_figure` / `save_figure` on the matplotlib backend). That way `saveas`, the desktop figure manager and `get` always agree.
- **Handles are doubles.** A figure's handle is its `Number`. Every other object gets a unique non-integer id, so a line can never alias a figure. `isequal(gcf, f)` works.
- **MATLAB placement rules.** `plot` draws into the current axes of the current figure and creates them if needed. With `NextPlot = 'replace'` (hold off), the axes are reset (children, title, labels, grid, limit modes). `hold on` adds and continues the ColorOrder. `subplot` reuses a matching slot and deletes overlapping axes.
- **get/set.** Property names are case-insensitive and unknown names error with `MATLAB:class:InvalidProperty`. `Type`, `Parent`, `Children`, `Number` and `Values` are read-only. Colours are validated (LineSpec letters, names, RGB in [0,1]). Setting limits flips the mode to manual. `Children` are listed newest first; a legend is not a child of its axes (modern MATLAB).
- **Statements print nothing.** `plot(...)`, `title(...)`, `hold on`, `close all`, … as statements produce no display and no `ans`.
- **`delete(filename)` keeps deleting files.** Only numeric handles go to the graphics path.

## Existing tests changed (both user-approved, 2026-10-13)
- `tests/unit/test_plot.py::test_host_surface_and_eval_builtin`: `h = plot(...)` is now a Line (`get(h,'Type')` is `'line'`, and its grandparent is figure 1) instead of the figure number. Evidence: MATLAB documents that `p = plot(___)` returns chart line objects.
- `tests/unit/test_workbench.py::test_figure_manager_list_close_focus`: a second `plot` reuses the current figure (1 figure). A second window needs `figure; plot(...)`, and a single-figure assertion was added. Evidence: MATLAB's `plot`/`hold` docs.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| Unknown or read-only property, bad colour, deleted handle | MATLAB-style errors. Covered by a test. |
| x/y length mismatch, `subplot(2,2,5)` | Errors. Covered by a test. |
| Matrix `plot` | One line per column, returned as a column of handles. Covered by a test. |
| Hold off resets the title | Reset. Covered by a test. |
| `saveas` to .fig | Clear "not supported" error (residual). Covered by a test. |
| `delete('file')` collision | Still deletes the file. Covered by a test. |
| Host closes a figure from the desktop | The model syncs from the backend on the next call. |

## Residuals
#593.
