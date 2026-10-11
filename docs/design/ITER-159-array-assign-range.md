# Design: range / non-scalar indexed assignment (Issue #159)

**Epic:** #158 · Absorbs #121, #122

## Decision
Extend `ArrayBackend.set_index` (COW) beyond scalar MVP:

1. **Linear** `A(idx)=rhs` where `idx` may be a vector (e.g. `1:3`):
   - scalar RHS → broadcast to all selected positions (column-major flat).
   - non-scalar RHS → `numel(rhs)==numel(idx)`; write in column-major order of RHS.
2. **2-sub** `A(r,c)=rhs` where `r`/`c` may be vectors:
   - selects `numel(r)×numel(c)` block via `np.ix_`.
   - scalar RHS broadcasts; else RHS numel must match; reshape to `(len(r),len(c))` Fortran order.
3. Mismatch → `NumericsError` → EvalError at assign seam.

## Non-goals
Logical LHS, `A(i)=[]` delete, grow-on-write, N-D, cell range assign.
