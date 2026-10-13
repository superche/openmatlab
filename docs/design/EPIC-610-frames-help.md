# Design: Epic #610, caller/base workspaces and help browsing (M7 C11)

Covers #608, which you ruled P0 on 2026-10-13: `evalin`, `assignin`, `doc`, `lookfor`, `what`.

## First principles
- **An explicit call-frame stack** (`runtime/frames.py`, a ContextVar of evaluators). Every place that calls a function pushes the calling evaluator for the duration of the call: `_invoke_call`, statement-form M-file calls, function-handle calls, `feval` and object method calls. In the callee:
  - **caller** is the top of the stack, and **base** is the bottom (the command-line evaluator);
  - with an empty stack the running evaluator is the base, and `evalin('caller', …)` at the prompt runs in base (MATLAB).
- **Balanced by construction.** Push and pop go through a context manager, so errors unwind the stack (covered by a test). Nested sessions (`str2num`) run under `frames.isolated()`, so their base is themselves.
- **evalin runs in the target frame.** It reuses `eval`'s semantics (value form, statement form, catch string) on the target evaluator, with the stack trimmed below the target. A chained `evalin('caller', …)` inside it therefore sees the target's own caller.
- **assignin** validates the name (MATLAB identifier, not a keyword) and errors with `MATLAB:assignin:invalidVariableName`. A bad context errors with `MATLAB:evalin:invalidContext`.
- **Anonymous functions and cellfun.** The workspace that invokes the handle is the caller. For `cellfun`, that is the workspace that called `cellfun`, because a builtin is not a MATLAB frame.
- **doc** prints the function's help text (there is no browser in a terminal) and says "No documentation found" otherwise. Bare `doc` points to `help`.
- **lookfor** searches H1 lines (and the whole file with `-all`) of the M-files in the current folder and on the path, plus builtin names. It prints `name - H1`.
- **what** prints MATLAB's grouped listing (code files, MAT-files, classes, packages). With an output it returns a struct with `path`, `m`, `mlapp`, `mlx`, `mat`, `mex`, `p`, `classes`, `packages`, or a 0x1 struct when the folder is missing.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| Nested calls (local function inside a function): sets land in the right frame and not in base | Covered by a test. |
| Error inside the callee leaves the stack unwound | Covered by a test. |
| Anonymous function and cellfun caller | Covered by a test. |
| Nested `str2num` session | Isolated. Covered by a test. |
| Bad context, keyword or invalid name | MATLAB IDs. Covered by tests and conformance. |
| Missing folder in `what`, unknown name in `doc` | Empty struct; "No documentation found". Covered by a test. |

## Residuals
#611.
