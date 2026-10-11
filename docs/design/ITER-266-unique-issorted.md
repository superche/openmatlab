# Design: unique / issorted (Issue #266)

**Epic:** #265 · Absorbs #97 · M2 C09

## Decision
1. `unique(A)` for vectors: sorted unique values; preserve row/col orientation. Matrix (no `'rows'`): column-major flatten → column of sorted unique.
2. `issorted(A)` for vectors/along first non-singleton dim: true iff non-decreasing (`diff >= 0`); return logical scalar. Empty → true.

## Non-goals
`'rows'`; index outputs; `'stable'`; `'descend'` for issorted.
