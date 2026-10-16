# Epic #767 (M13 G-E0): Workbench output routing to the Command Window

Fixes #760. Milestone: [M13 Graphics completion](../milestones/M13-graphics.md), criterion G09 (first half).

## Problem

Builtins write to the process streams (`fprintf` fid 1/2 via `sys.stdout`/`sys.stderr`, `warning`, `toc`, `whos`, table display, `dbstack` …). Only value display went through `session.display` (the Command Window buffer), so in the tk Workbench a script's `fprintf`/`disp`/warning text appeared on the launching terminal.

## Design

- `host/workbench.py` installs a `_RoutedStream` proxy on `sys.stdout` and `sys.stderr` (once, idempotently). Each proxy has a **thread-local target**.
- `CommandWindow.eval` wraps evaluation in `_route_output(self._stream)`: on the evaluating thread (the main thread headless, the `openmatlab-run` worker thread in the tk app) every write goes to that Command Window's transcript, in order with value display and error text.
- Other threads (the tk main loop, test runners, other Workbenches) keep the original stream. Nested targets are saved and restored, so two Workbenches never mix output.
- `evalc` keeps working: it swaps `sys.stdout` with `redirect_stdout` for its call and then restores the proxy.
- New helpers: `CommandWindow.text()` (whole transcript) and `Workbench.run_file(path)` (open + Run).

MATLAB behaviour (public docs, "Command Window"): output of `fprintf(1,…)`, `disp`, warnings and errors from scripts and functions run from the desktop is shown in the Command Window. `fprintf(2,…)` is shown there too (MATLAB colours it red; we do not colour it yet).

## Adversarial review

| Attack | Result |
|---|---|
| Output from a function file called by a script | Routed (`test_function_file_output_routed`) |
| Output then uncaught error | Order kept, MATLAB error text, no traceback (`test_output_before_error_and_error_text_in_order`) |
| `evalc` inside the Workbench | Still captured, not leaked to the transcript |
| A different thread prints while a Workbench is idle | Goes to the terminal (`test_other_threads_not_routed`) |
| Two Workbenches in one process | Isolated transcripts |
| pytest/IDE replaces `sys.stdout` between runs | Proxy is re-installed on top of the current stream on the next eval |
| `isatty`/`encoding` lookups on the proxy | Delegated to the original stream |
| Debugger `K>>` output | Already on `debugger.out` = Command Window buffer; unchanged |

Residuals: stderr text is not coloured red in the tk Command Window; filed as an issue.
