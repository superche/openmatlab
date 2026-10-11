# Design: cell content assignment (Issue #103)

**Epic:** #102 · Absorbs #79

## Decision
- AST: `CellAssign(target: CellIndexExpr, value: Expr, suppress: bool)`.
- Parser: after parsing an expression, if `=` follows and LHS is `CellIndexExpr` → `CellAssign`; else `ExprStmt` (fixes leftover `=` hazard).
- Runtime: `CellValue.with_set(i, j, value)` returns a new frozen cell; workspace name updated.
- Indices: same 1-based linear / (i,j) rules as read (`_cell_subscripts` helper shared with read).
- OOB → `EvalError` (no grow).

## Non-goals
Grow-on-assign, `c(i)=[]` delete, array `A(i)=v` assignment.
