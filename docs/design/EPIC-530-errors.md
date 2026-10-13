# Design: Epic #530, errors and exceptions (M7 C01)

Covers #540 (try/catch + error/MException) and #541 (assert, lasterr, MATLAB ids on builtin errors).

## First principles
- **One error type.** Every user-visible failure is an `EvalError`. It now carries an `identifier` (default `''`). Builtins raise `EvalError(msg, identifier=...)` directly, so the evaluator's `"name: msg"` rewrap of `ValueError` never prefixes a user's `error()` text.
- **Catch everything the user could see, nothing that is control flow.** `try` catches any `Exception` from its body, including non-`EvalError`s, which are wrapped (MATLAB code can catch any error). `_BreakSignal`, `_ContinueSignal` and `_ReturnSignal` are re-raised first, so `break`, `continue` and `return` inside `try` behave as in MATLAB.
- **MException is a struct-shaped object.** `MExceptionValue(StructValue)` has the fields `identifier`, `message` and `stack`. Field reads (`e.message`) reuse the struct path. `class` returns `MException`, `isstruct` returns false, and display shows `MException with properties:`.
- **Identifiers for runtime errors** are inferred from the message in a single table (`runtime/errors.py`): `MATLAB:badsubscript`, `MATLAB:UndefinedFunction`, `MATLAB:TooManyInputs`, `MATLAB:minrhs`, `MATLAB:sizeDimensionsMustMatch`, `MATLAB:subsassigndimmismatch`, `MATLAB:index:expected_positive_integer`. An explicit id always wins.
- **MATLAB argument rules for `error`.** With one argument the text is literal: no format processing, so `'100%'` and `'\n'` stay as typed. With `error(id, fmt, ...)` the first argument is an id when it matches `comp:mnemonic`; otherwise `error(fmt, args...)` formats. `error('')` and an empty-message struct are no-ops. `error(struct)` reads `message` and `identifier`.
- **lasterr** is updated every time `try` catches an error. `[msg, id] = lasterr` is supported.

## Grammar
`try sep body [catch [IDENT] sep handler] end`. `IDENT` is the exception variable only when a separator, `end` or EOF follows it. So `catch disp('h')` is a handler statement, as in MATLAB.

## Files
`lang/tokens.py`, `lang/lexer.py` (KW_TRY/KW_CATCH), `lang/ast_nodes.py` (`TryStmt`), `lang/parser.py` (`parse_try`), `runtime/evaluator.py` (`EvalError.identifier`, `_eval_try`), `runtime/errors.py` (new), `libs/error_builtins.py` (new: `error MException throw rethrow assert lasterr getReport`, and `isstruct` for MException), `host/display.py` (header).

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| `break` / `continue` / `return` inside `try` swallowed by the handler | Re-raised before the generic handler. Covered by a BDD loop scenario and by `test_return_inside_try_in_function_not_caught`. |
| `catch disp('h')` misread as `catch disp` plus garbage | Ident lookahead requires a separator. Covered by `test_parse_catch_call_is_handler_not_ident`. |
| `error('100%')` crashes in the formatter, or `'%%'` collapses | The one-argument form is literal. Covered by a test and by conformance `lit_ok`. |
| `error('val %d', 9)` treated as an id | Ids need `a:b` with no spaces. Formatted, empty id. |
| User `error()` gets an `error: ` prefix from the builtin rewrap | Raises `EvalError` directly. Covered by conformance `msg_ok`. |
| Error raised inside a called `.m` function | Propagates to the caller's `catch` with its id. Covered by `test_error_from_function_caught_by_caller`. |
| `assert([])` passes vacuously | An empty condition fails, as in MATLAB. |
| Internal (non-EvalError) exception inside `try` | Caught and wrapped. An uncaught one still reaches the #529 CLI guard, so no traceback. |
| `MException('bad','x')` | Rejected with `MATLAB:MException:invalidId`. |
| Octave-style ids (`Octave:some-id`) | Accepted (hyphen allowed). |
| Gaps | The size-mismatch message text, `stack` contents, `getReport` trace, `addCause` and `lasterror` struct are filed as **#565** (p2). |
