# Design: return in functions/scripts (Issue #137)

**Epic:** #136 · Absorbs #131

## Decision
- Lexer keyword `return` → `KW_RETURN` (token already reserved).
- AST: `ReturnStmt`.
- Evaluator: `_ReturnSignal`; allowed when `_return_ok > 0`.
- `eval_program` (scripts via `run`/`eval_script`) and `MFileCallable` body bump `_return_ok`.
- Top-level REPL/`-e` uses per-stmt eval without bump → `EvalError`.
- No return-value expression; outputs are whatever was assigned (MATLAB-like).

## Non-goals
`return expr`, nested function return targeting outer, switch.
