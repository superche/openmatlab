# Epic #700 (D-E3): keyboard, input and condition stops

Milestone: [M11 Debugger and Workbench](../milestones/M11-debugger-workbench.md), criteria D06 and D07 (absorbs the `input`/`keyboard` part of #577).

## Design (built on the D-E2 pause model)

- **`keyboard`** enters the existing paused loop at the current line (`Debugger.keyboard`). Nothing is printed before `K>>`, as in MATLAB. `dbcont` resumes and `dbquit` stops the run.
- **`input(prompt)` / `input(prompt,'s')`** read one line from the same input source as `K>>`: the queued lines (`ReplSession.feed_input`), then the Workbench queue, then the console. Without `'s'`, the reply is evaluated as one expression in the **caller's** workspace, and an empty reply gives `[]`. A bad reply is reported and the prompt is shown again. End of input raises `MATLAB:input:EndOfInput`, so a non-interactive run never hangs.
- **Error stops.** `Evaluator.eval_stmt` calls `debugger.on_error` when a statement inside a function frame raises. This happens at the innermost statement, before unwinding, so the stack and the faulting line are intact. An error is *caught* when it is raised inside a `try` body: a `TRY_DEPTH` ContextVar is incremented by `_eval_try` and is reset before the `catch` block runs. `if caught error [ID]` stops on caught errors only, and `if error [ID]` on uncaught errors only, matching MATLAB. Each exception stops at most once (`_db_seen`).
- **`if warning [ID]`** is triggered from `warnings.emit` after the warning is printed, and pauses in the top frame at its current line.
- **`if naninf`** is checked by `debugger.on_value` after each statement in a function frame whose numeric result contains NaN or Inf.
- **Cost.** Every hook is behind the existing `debugger.ON` flag, which is already true whenever a condition stop is set, so code without breakpoints pays nothing new.

## Adversarial review

- **Probe sweep:** `input()`, a non-text prompt, a bad option, `keyboard(1)`, end of input, and `dbquit` from `keyboard` all raise MATLAB errors or unwind cleanly, with no traceback (`tests/unit/test_condition_stops.py`). `dbcont` after an uncaught-error stop lets the error reach the prompt.
- **Nested try:** the catch block runs with the outer depth restored, so an error inside `catch` is *uncaught* unless an outer `try` exists.
- **No existing test was changed;** D04 and the hook-overhead micro-check still pass.
- **Deferred (residual #729):** naninf granularity, error-stop message fidelity, stops at the base workspace, a dedicated Workbench input prompt, and condition stops in `dbstatus` output.
