# Design: minimal control flow (Issue #22)

**Epic:** #19 · **KISS**

## Choice
- `if` / `elseif` / `else` / `end`
- Loop: **`for i = a:b … end`** (not `while` in this MVP)
- Relational: `< <= > >= == ~=` as `BinOp`; condition truth = scalar ≠ 0

## AST
`IfStmt`, `ForStmt`; bodies are statement lists (nesting via recursive parse).

## Non-goals
`while`, `break`/`continue`, `switch`, short-circuit `&&`/`||`, matrix-valued conditions beyond “all nonzero”.
