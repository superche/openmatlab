# Design: grow-on-assign (Issue #254)

**Epic:** #253 · Absorbs #119 #108 · M2 C08

## Decision
1. `set_index` linear: if max index > numel, expand vector (row→wider row, col→taller col; matrix linear → column of new numel) with zeros, then assign.
2. `set_index` 2-sub: if i>rows or j>cols, expand to max dims with zeros, then assign.
3. `c{i}=` / `c{i,j}=`: expand CellValue grid with empty doubles, then `with_set`.

## Non-goals
N-D; custom fill; grow on read.
