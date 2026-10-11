# Design: cumsum (Issue #88)

**Epic:** #87 · Absorbs part of #73

## Decision
- `cumsum(A)` along first non-singleton dim; `cumsum(A, dim)` (1-based dim).
- Result same shape as `A` (cumulative along axis).
- Empty `[]` → `[]`. `dim > 2` → return `A` unchanged (2-D MVP).
- Same `libs.numeric_builtins` seam as Epic #4.
