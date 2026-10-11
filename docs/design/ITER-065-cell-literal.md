# Design: cell literals + CellValue (Issue #65)

**Epic:** #63 · **KISS / public MATLAB doc semantics**

## Decision
- AST: `CellLiteral(rows: tuple[tuple[Expr, ...], ...])` — same shape as MatrixLiteral.
- Runtime: `CellValue(rows: tuple[tuple[Value, ...], ...])` with `matlab_class()=="cell"`, `shape`, `numel`.
- Parser: `{` … `}` via `_parse_cell_literal` (row/`;`/juxtaposition like matrices; elements are full expressions).
- Evaluator: eval each element as `Value` (Array / CharValue / nested CellValue) — **no** scalar-only restriction.
- Display: `ConsoleDisplay` prints `{m×n cell}` then each `c{i,j}` line (MATLAB-ish summary).
- Empty `{}` → 0×0 cell.

## Non-goals
Content indexing (→ #66), `()` cell indexing, assignment into cells, comma-separated lists.
