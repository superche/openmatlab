# Epic #699 (D-E2): debug engine and pause model

Milestone: [M11 Debugger and Workbench](../milestones/M11-debugger-workbench.md), criteria D03, D04 and D05. This design doc is written and committed before the implementation, as the approved plan requires.

## Options considered for the pause model

| Option | How it pauses | Good | Bad |
|---|---|---|---|
| A. Re-entrant nested REPL (chosen) | the statement hook calls `Debugger.pause()`, which runs a `K>>` read–eval loop *inside* the paused Python call, until `dbcont`/`dbstep`/`dbquit` | KISS; the Python stack *is* the MATLAB stack, so frames, workspaces, `evalin` and `dbup` need nothing new; deterministic for tests (input from a queue) | blocks its thread while paused, so a GUI must run user code off the UI thread |
| B. Evaluator thread with a command queue | user code runs in a worker thread; the hook blocks on a queue the UI feeds | the UI stays responsive | threads leak into every test; ContextVars must be copied; harder to make deterministic |
| C. Generator / CPS evaluator | every eval method yields | no blocking at all | rewrites the 2,000-line evaluator; high risk |

**Decision: A** for the engine. Option B is layered on top of A in D-E4 for the tkinter Workbench: the Workbench runs `ReplSession.run_line` in a worker thread, and its paused-input source is a blocking queue that the toolbar and command window feed. The engine needs no change for that, because the input source is pluggable.

## Engine

- `runtime/debugger.py`, one `Debugger` per `Session` (`session.debugger`). `ReplSession.run_line` makes it active through a ContextVar, so several sessions in one process stay separate.
- **Hook.** `Evaluator.eval_stmt` already updates `frame.line` (D-E1). When the module flag `debugger.ON` is set (there are breakpoints or a step is pending), it also calls `debugger.on_statement(ev, frame, stmt)`. With no breakpoints the cost is one global read per statement.
- **Breakpoints** are keyed by resolved file path, mapping a line to an optional condition. `dbstop in f at N` snaps N to the next executable statement line in that file, `dbstop in f` uses the first executable line of `f`, and `dbstop … if expr` evaluates `expr` in the paused frame. `dbclear` (all / in f / in f at N) and `dbstatus` (an n×1 struct with `name`, `file`, `line`, `anonymous`, `expression`, `cond`, `identifier`, plus a printed form) complete the set.
- **Stepping** works on the call-stack depth: `dbstep` pauses at the next statement with depth ≤ the current depth, `dbstep in` at the next statement at any depth, `dbstep out` at depth < the current depth, and `dbstep N` repeats `N` times. `dbcont` resumes. `dbquit` raises `DbQuit`, a `BaseException`, so `try/catch` cannot swallow it; `run_line` absorbs it and returns to the prompt.
- **Paused workspace.** Each call-stack frame records its evaluator (`Frame.ev`). `K>>` lines are evaluated in the evaluator of the *active* frame, so assignments are visible when execution resumes. `dbup`/`dbdown` move the active frame, and moving up past the outermost frame reaches the base workspace. `who`, `exist` and `evalin('caller')` follow, because they use the same workspace and evaluator stack.
- **Input source.** Lines come from `Debugger.inputs` (filled by `ReplSession.feed_input(lines)` for scripts and tests, and later by the Workbench), and otherwise from the console with the prompt `K>> `. End of input means `dbquit`, so a non-interactive run never hangs.
- **Messages.** On pause the engine prints `N   <source line>`. Debug commands used outside debug mode give MATLAB errors, never tracebacks.

## Risks and checks

- **Overhead:** the hook is guarded by a module boolean. `tests/unit/test_debugger.py` has a micro-check that a 20k-iteration loop with no breakpoints runs within 1.5× of the same loop with the flag forced off.
- **Re-entrancy:** a breakpoint hit while a `K>>` command runs (for example, calling the same function from the prompt) nests another pause. MATLAB allows this; each level resumes independently.
- **Out of scope here:** condition stops (`if error`/`warning`/`naninf`) and `keyboard`/`input` are D-E3. The UI is D-E4.
