# Design: parentheses cell indexing c(i) (Issue #104)

**Epic:** #102 · Absorbs #82

## Decision
- When `IndexExpr` / call-or-index resolves a **bound CellValue**, `()` is cell **slice** (not content): returns a `CellValue` containing the selected contents.
- `c(k)` linear → 1×1 cell; `c(i,j)` → 1×1 cell.
- Reuse `_cell_subscripts` for bounds.
- Non-cell targets unchanged (Array index / function call).

## Non-goals
Multi-element slices `c(1:2)`, `c(:,1)`, assignment via `c(i)=…`.
