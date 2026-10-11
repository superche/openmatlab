# Design: continue in for/while (Issue #127)

**Epic:** #126

## Decision
- Lexer: keyword `continue` → `KW_CONTINUE`.
- AST: `ContinueStmt` (like `BreakStmt`).
- Evaluator: `_ContinueSignal`; in `_eval_for` / `_eval_while` body loop → Python `continue`.
- `continue` outside any loop → `EvalError`.
- Nested loops: signal caught only by innermost for/while (same as break).

## Non-goals
Labeled continue, continue from switch (no switch yet).
