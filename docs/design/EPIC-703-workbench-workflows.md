# Epic #703 (D-E6): Workbench workflows

Milestone: [M11 Debugger and Workbench](../milestones/M11-debugger-workbench.md), criterion D10.

## Design

- **Code sections.** `EditorPanel.sections()` returns 1-based inclusive line ranges. A line whose first non-blank characters are `%%` followed by a space or the end of the line starts a section (MATLAB); `%%%` and `%%x` do not. Code before the first marker is a section of its own. `set_cursor_line`/`cursor_line` hold the caret; `section_at`/`section_text` give the caret's section.
- **Run Section / Run and Advance.** `Workbench.run_section()` evaluates the caret's section in the base workspace through the debug controller, so breakpoints can pause it. `run_and_advance()` does the same, then moves the caret to the first line of the next section; on the last section the caret stays. Editor runs are not added to the Command History (MATLAB). Toolstrip buttons **Run Section** and **Run and Advance**, and Ctrl+Enter / Ctrl+Shift+Enter, drive them.
- **Run with breakpoints.** `run_file()` saves a dirty file and runs it with `run('<file>')` through the controller (same path as the D-E4 Run button).
- **Error hyperlinks.** `Workbench.eval` no longer lets an evaluation error escape: the Command Window shows the CLI layout (`error: <message>`, then one `Error in f (line N)` line per frame), never a traceback. `CommandWindow.last_error_location()` is the top file frame `(file, line)` or `None`; `open_error_link()` opens that file in the Editor with the caret on the line. In tk, `Error in …` lines are underlined links.
- **Command History re-run.** `CommandWindow.rerun_history(i)` re-evaluates entry `i` (Python-style index, -1 = newest) and appends it again, as MATLAB does. tk adds a Command History list; double-click or Enter re-runs an entry.
- **Compat.** `EditorPanel.tab_title` stays a string property and is also callable (`ed.tab_title()`).

## Adversarial review

| Probe | Finding | Resolution |
|---|---|---|
| `%%%`, `%%x`, indented `%%`, leading code, empty buffer | marker rules | `test_section_markers` |
| Run and Advance on the last section | caret must not move past the end | stays; `test_run_section_and_advance` |
| tk caret defaulted to the end of the text, so Run Section ran the last section | wrong section | the tk caret is initialised from the model caret |
| Error in a section / at the prompt | previously a raised `EvalError` (traceback risk in callers) | caught, shown as MATLAB-style text; `test_section_error_is_reported_not_raised` |
| Error with no file frame (undefined variable) | stale link from an earlier error | location reset to `None`; `test_error_link` |
| Re-running a history entry while paused | must go to `K>>` | tk path sends it to the debugger |
| Section error line numbers / unsaved-buffer breakpoints | relative to the section | residual #751 |
