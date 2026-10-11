# Design: while + break (Issue #34)

**Epic:** #33 · **KISS**

## Decision
- Keywords: `while`, `break` (no `continue` this epic)
- AST: `WhileStmt(condition, body)`, `BreakStmt`
- Eval: `_BreakSignal` exception caught by `_eval_while` / `_eval_for` only
- Truthiness: reuse `_truthy` (scalar ≠ 0 / all nonzero)

## Non-goals
`continue`, `switch`, infinite-loop guards beyond normal Python recursion/stack.
