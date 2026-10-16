# Epic #701 (D-E4): Workbench debug UI

Milestone: [M11 Debugger and Workbench](../milestones/M11-debugger-workbench.md), criterion D08.

## Design

- **Threading.** This is option B of the [pause-model design](EPIC-699-pause-model.md), layered on the D-E2 engine. `host/debug_ui.py` `DebugController` runs user code in a worker thread. The engine's paused-input hook (`Debugger.read_line`) blocks on a queue, and the controller marks the state `paused` as it waits. Each toolbar action (Continue, Step, Step In, Step Out, Quit Debugging, which map to `dbcont`, `dbstep`, `dbstep in`, `dbstep out` and `dbquit`) puts one line on the queue and waits for the code to pause again or finish. The headless model is therefore deterministic, and tk widgets are only touched on the UI thread.
- **Gutter.** `EditorPanel.toggle_breakpoint(line)` uses the same line snapping as `dbstop` (the next executable line) and toggles the breakpoint in the session debugger, so the gutter and `dbstatus`/`dbclear` share one source of truth. `EditorPanel.breakpoints()` returns the lines as a MATLAB row vector (1×N, or 0×0 when there are none), like `dbstatus(file).line`.
- **Current line, stack and Workspace.** `debug.stack()` lists `(name, file, line)` with the current frame first, as `dbstack` does. `select_frame(k)` moves the active frame (0 is the current frame, 1 its caller), which is the same as `dbup` k times. `current_line()`/`current_file()` follow the selected frame. The Workspace panel (`wb.workspace`) reads the selected frame's workspace while paused, and the base workspace otherwise.
- **Command Window.** While paused, `wb.eval` sends the line to `K>>`, so it is evaluated in the selected frame and assignments take effect on resume. The tk prompt label changes to `K>>`.
- **Engine changes.**
  - `dbstep out` now pauses in the caller at the call line as soon as the function returns (MATLAB behaviour). The hook is in `callstack.entering` and runs on normal return only. D04's expected trace is unchanged.
  - `debugger._ALL` is now a `WeakSet`, so dead sessions no longer keep the statement hook on.
  - `Workbench.create(cwd=...)` puts the Current Folder on the search path, as MATLAB does.
- **tk chrome (`run_tk`).**
  - A debug toolbar and a stack selector combobox sit above the editor tabs.
  - Each editor tab has a line-number gutter: click it or press F12 to toggle a breakpoint, shown as a dot and a red line.
  - A yellow current-line marker follows the selected frame, and the paused file opens automatically.
  - Run executes the saved file through the controller, so its breakpoints apply.

## Adversarial review

- **Misuse:** Step while not paused, an invalid stack frame, or Run while already running raise `DebugError`. User errors in a debug run are printed in the Command Window, never as tracebacks.
- **No hangs:** every wait has a 60 s timeout, and end of input still means `dbquit` (engine). Test fixtures quit and `dbclear all` on teardown.
- **Hook overhead:** the existing micro-check still passes. When only other (dead) sessions keep the flag on, `_recompute_on` collects garbage once before deciding.
- **tk:** `tests/unit/test_workbench_debug.py::test_tk_debug_chrome` drives the real widgets (Run, Step, Step In, the stack combobox, Continue) under a display, and is skipped when there is none. Tabs that are rebuilt are now destroyed rather than leaked.
- **No existing test was changed.**
- **Deferred (residual #725):** a Pause button for long runs, conditional breakpoints from the gutter, and `Step` at the end of a function (#713).
