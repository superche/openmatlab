# Design: Epic #531, functions (M7 C02)

Covers #542 (varargin/varargout, nargin/nargout and the chk functions), #543 (global/persistent) and #544 (eval/feval/exist/str2func/func2str). #529 (local functions in scripts) shipped first, in PR #564.

## First principles
- **MATLAB calling convention.**
  - A call may pass *fewer* inputs than declared; an unset input errors only when it is read. Passing *more* than declared raises `MATLAB:TooManyInputs`, unless the function declares `varargin`.
  - `varargin` is a 1×N cell. Any value can be an argument: cell, struct, handle, char.
  - Outputs are collected up to `max(nargout, 1)`. An output that is requested but not assigned raises `MATLAB:unassignedOutputs`.
  - `varargout` expands into the requested outputs.
  - A statement call `f();` runs with `nargout == 0`, so an unassigned output is not an error.
- **Frame intrinsics.** `nargin`, `nargout`, `narginchk`, `nargoutchk`, `eval`, `feval`, `exist`, `str2func` and `func2str` need the *calling* frame. They live in `libs/function_intrinsics.py` and `_invoke_call` dispatches them before the builtin table.
  - The callee evaluator carries `_nargs = (nargin, nargout)` and `_persist_key`.
  - `nargin('f')` and `nargout(@f)` return the declared counts, negative when variadic.
- **global / persistent are aliases.**
  - The `global` and `persistent` keywords parse to `DeclStmt`.
  - `Workspace.bind_ref(name, store, [])` makes the name in the current frame read and write a shared store, initialised to `[]`.
  - Globals use one store per session resolver (`FunctionResolver.global_store`). Persistents use one store per `(file, function)`.
  - `persistent` outside a function is an error, as in MATLAB.
- **eval.**
  - In value form, `v = eval('expr')`, the expression is evaluated without display.
  - In statement form the code runs in the caller's workspace and displays itself.
  - With `eval(try, catch)`, any error, parse errors included, runs the catch string and updates `lasterr`.
- **Operator functions** such as `plus` and `mtimes`, through `horzcat`/`vertcat`, evaluate the real operator expression. One semantics, no drift. This makes `feval(@plus, ...)` and `cellfun(@plus, ...)` work.
- **func2str** prints anonymous bodies without blanks outside quotes (`@(x)x+1`). For named handles it gives the bare name. **str2func** of an unknown name defers the error to the call, as MATLAB does.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| `break` or `return` inside a function body under `eval` | Control signals are never swallowed by the eval catch string. |
| `noout()` as a statement errors on its unassigned output | Statement calls use nargout 0. Covered by `test_unassigned_output_error`. |
| `[a,b,c] = f()` with varargout, but only `nargout` values assigned | Expanded in order; a missing one raises `unassignedOutputs`. |
| A `global` redeclared after a local of the same name | The existing local value is adopted when the global is new. Otherwise the store wins. |
| Persistent state leaking between different functions with the same name in different files | The key includes the source path. |
| `func2str(@() disp('a b'))` loses the space inside the quotes | A quote-aware canonicaliser. Covered by a test. |
| `eval('x = (')` raises a Python ParseError | Converted to an `EvalError`. Covered by a test. |
| `v = eval('1+2')` also prints `ans` | The value form does not display. |
| Old `args must be Arrays` limit (no cell or struct args) | Removed. Covered by `test_cell_and_struct_args_accepted`. |
| Gaps | Multi-collection `cellfun`, the bare `nargin` message, `evalin`/`assignin`, and `clear` of globals are filed as **#569** (p1). |
