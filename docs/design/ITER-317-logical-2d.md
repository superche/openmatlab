# Design: 2-D logical indexing (Issue #317)

**Epic:** #316 · Absorbs #237

## Decision
In `index` / `set_index` for 2 subscripts: if a subscript is logical, require `numel(mask)==dim_size`, convert to 0-based (or 1-based) positions via `nonzero`. Mix with colon/integer OK. Empty mask → 0 rows or 0 cols.

## Non-goals
true/false keywords; N-D; 2-D logical delete.
