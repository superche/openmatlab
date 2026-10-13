# Design: Epic #532, command syntax and workspace commands (M7 C03)

Covers #545 (command syntax) and #546 (workspace and session commands).

## First principles
- **Command syntax is lexical, decided at statement start.** When an identifier begins a statement at nesting depth 0 and is followed by blanks, the lexer looks at the next character:
  - It is *not* a command when that character is a separator (`; , %` or newline), `(`, a lone `=`, or a binary operator *followed by a blank* (`a - b`, `a == b`). Relational and logical operators always read as an expression.
  - Anything else makes the statement a command: `format long`, `a -b`, `disp 'x y'`.
  - The arguments are blank-separated words. `'...'` groups a word and the quotes are removed (`''` is one quote). The command ends at `; , %` or newline.
  - This is the documented MATLAB rule.
- **One AST, one call path.** A command becomes `CommandStmt`, a subclass of `ExprStmt` whose expression is `name('arg1', 'arg2')`. Display, `ans` and errors are therefore exactly those of the function call.
- **Variables win.** MATLAB treats a name that is a variable as an expression. At run time, if `name` is bound, the stored `raw` text is re-parsed with command detection off. So `a = 3; a -1` gives `ans = 2`.
- **Statement forms print, value forms return.**
  - `clear`, `clearvars`, `who`, `whos`, `format`, `clc`, `help`, `cd`, `dir`, `ls` and `eval` run with `nargout = 0` when used as a statement. They print the MATLAB listing and leave `ans` alone.
  - With an output (`w = who`, `s = whos`, `L = dir`) they return a cell, struct array or char.
  - `which name` (command form) prints `built-in (...)`, the path, or `x is a variable.`. The function form `which('x')` keeps returning the path string, as before.
- **format** is display state (`host.display.FORMAT`): 4 or 15 digits for real scalars and matrices, `%.4e` or `%.15e` for scalars in scientific form. `format` alone resets.
- **evalc** temporarily installs a capturing `ConsoleDisplay` and redirects stdout, so it captures both `disp` output and statement echo.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| `a - b`, `a == b`, `x = 1`, `x(2) = 3`, `a'`, `a + 1` misread as commands | Covered by the `test_expression_not_command` parametrisation. All 1181 existing tests are unchanged and pass, which means existing scripts were not reinterpreted. |
| `a -1` when `a` is a variable | Re-read as an expression. Covered by a unit test and BDD. |
| A command swallowing the rest of the line after `;` or `%` | Covered by `test_command_ends_at_separators_and_comment`. |
| Command detection inside `f(a, b c)` or `[...]` | Only at nesting depth 0 and at statement start. |
| `which("add2")` statement semantics (existing test expects `ans`) | The function form is unchanged. Only the command form prints. No existing test was changed. |
| `cd` leaking into other tests | The unit fixture restores cwd and format. The conformance script `cd`s back itself. |
| `clear global G` leaves an alias | Removes the store entry and the frame binding. Covered by a test. |
| `format nonsense` | `MATLAB:format:unknownFormat`. |
| Gaps | Format G/compact/rat modes, per-session format, `dir` column layout, `more`/`diary` are filed as **#573** (p2). |
