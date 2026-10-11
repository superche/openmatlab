# Design: cell content indexing + cell(m,n) (Issue #66)

**Epic:** #63 · **KISS / public MATLAB doc semantics**

## Decision
- AST: `CellIndexExpr(target, indices)` — postfix `{…}` distinct from `(…)` `IndexExpr`.
- Parser `parse_postfix`: after primary, loop also matches `LBRACE` → cell content index.
- Evaluator: require `CellValue`; 1-based linear `c{k}` (column-major) or `c{i,j}`; return **content** Value.
- Out of range → `EvalError`.
- Builtin `cell(m,n)` / `cell(n)` / `cell()` → empty cells filled with 0×0 doubles (`CellValue.empty`), registered in `libs.numeric_builtins` (same seam as Epic #4).

## Non-goals
`c(i)` parentheses cell-slice, assignment `c{i}=…`, comma-separated list expansion, `cellfun`.
