# Epic #698 (D-E1): source positions and the MATLAB call stack

Milestone: [M11 Debugger and Workbench](../milestones/M11-debugger-workbench.md), criteria D01 and D02.

## Problem

`MException.stack` was always a 0×1 struct, `getReport` returned only the message, `dbstack` and `mfilename` did not exist, and uncaught errors gave no location (#565, #611). The parser dropped token lines, and the evaluator had no idea which file or line it was running.

## Design

1. **Lines on statements.** `Parser.parse_statement` records the line of a statement's first token as a private `_line` attribute on the (frozen) node, set with `object.__setattr__`. It is not a dataclass field, so node equality, hashing and every existing constructor stay unchanged. Every block body (if/for/while/try/switch/function, classdef methods) goes through `parse_statement`, so nested statements get lines too, relative to the file.
2. **Call stack.** A new `runtime/callstack.py` holds a ContextVar tuple of mutable `Frame(file, name, line)` objects. It is kept apart from `runtime/frames.py`, which tracks *evaluators* for evalin/assignin; the call stack tracks *source positions*. `MFileCallable.__call__` pushes a frame for every M-file function, local function and classdef method. `eval_script` pushes one for every script, whether it runs through `run` or by name.
3. **Line tracking.** `Evaluator.eval_stmt` writes `frame.line = stmt._line` before it executes a statement. That is one attribute write and costs about nothing; it is also the hook point D-E2 needs.
4. **Capturing the stack on errors.** On any exception, `eval_stmt` calls `callstack.attach(exc)`, which sets `exc.mstack` once. The innermost statement that raised wins, so outer frames do not overwrite it. `try/catch` builds `MException.stack` from it. `rethrow` restores the original stack; `throw` gets a fresh one at the throw site, as in MATLAB.
5. **Names.** `f` for a main function, `file>local` for local functions, `Class.method` for classdef methods (`MFileCallable.qualname`), and the script name for scripts.
6. **Builtins.** `dbstack` (with `n`, `'-completenames'`, a printed form, and a second output) and `mfilename` (with `'fullpath'` and `'class'`) are in `libs/debug_builtins.py`. `dbstack` is a statement-zero builtin, so a bare `dbstack` prints `> In f (line N)`.
7. **Reports.** `getReport(ME, 'extended'|'basic', 'hyperlinks', …)`. The extended form is `Error using <top> (line N)`, then the message, then `Error in <name> (line N)` for each outer frame. The basic form is the first two lines only. When the stack is empty (command-line errors), the report is the bare message, as before. The CLI prints the uncaught error followed by one `Error in f (line N)` line per frame.
8. **Cell transpose.** `c'` and `c.'` on 2-D cells were missing and were needed by D01/D02 (`fieldnames(...)'`). They are added in the evaluator; N-D cells raise MATLAB's `MATLAB:transpose:NDArray` error.

## Adversarial review

- **LSP and frozen nodes:** `_line` is not a field. `==`, `hash` and `replace` ignore it, so the AST caches and existing tests keep working. Nodes built without the parser have no `_line`, and the frame keeps its previous line.
- **Control-flow signals:** `_Break`, `_Continue` and `_Return` are re-raised before `attach`, so they carry no stack and cost nothing extra.
- **Non-EvalError exceptions** (Python errors that `try` turns into user errors) keep their stack: `_eval_try` copies `mstack` when it wraps them.
- **Errors raised while binding arguments** (too many inputs, and so on) are attributed to the caller's statement, as in MATLAB.
- **Isolation:** the stack is a ContextVar, so nested sessions and threads stay independent. Push and pop use a context manager, so errors unwind it.
- **Deferred (filed as a residual):** for errors raised by builtins, MATLAB's header names the builtin (`Error using plus`), while we name the M-file frame. Also deferred: nested-function names (`outer/inner`), anonymous-function frames, the line of the continuation part of multi-line statements, and frames for class property-default evaluation.
- **No existing test was changed.**
