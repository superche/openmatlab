# Design: indexed array assignment (Issue #116)

**Epic:** #115 · Absorbs #111

## Decision
- AST: `ArrayAssign(target: IndexExpr, value: Expr, suppress)`.
- Parser: LHS may be `IndexExpr` **or** `CellIndexExpr` (existing); error otherwise.
- Target of IndexExpr must be a `Name` bound to an `Array`.
- Numerics: `ArrayBackend.set_index(a, indices, value) -> Array` — copy-on-write, 1-based;
  one index → linear column-major; two → (row,col). Scalar RHS only.
- OOB → `NumericsError` / `EvalError`. No grow.

## Non-goals
Range LHS, logical index assign, grow, `A(i)=[]` delete, non-scalar RHS expand.
