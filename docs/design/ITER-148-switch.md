# Design: switch / case / otherwise (Issue #148)

**Epic:** #147 · Absorbs #132

## Decision
- Keywords: `switch`, `case`, `otherwise` (plus existing `end`).
- AST: `SwitchCase(values: Sequence[Expr], body)`, `SwitchStmt(expr, cases, otherwise)`.
- Case label forms:
  - `case <expr>` — match if switch value equals eval(expr) (scalar numeric / char).
  - `case {e1, e2, ...}` — CellLiteral; match if equals any element (MATLAB multi-case).
- Evaluator: evaluate switch expr once; first matching case body; else otherwise; else no-op. **No fall-through.**
- Equality: numeric scalars via float compare; CharValue string equality; size-1 arrays via scalar extract. Mismatch types → not equal.

## Non-goals
Fall-through; string class; pattern/regex cases; `case` comma-lists without braces.
