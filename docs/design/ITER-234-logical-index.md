# Design: logical indexing (Issue #234)

**Epic:** #233 · Absorbs #162 · M2 C07

## Decision
1. Relational ops return `NDArrayValue` with **bool** dtype; `matlab_class()` → `"logical"`.
2. Linear `index` / `set_index`: if index `matlab_class()=="logical"`, treat as mask over column-major flat (numel must match).
3. Read orientation: row source → row of hits; col → col; else column of hits (MATLAB `A(L)` for matrix is column).
4. Assign: scalar RHS broadcasts to selected; vector RHS numel must match nnz(mask).

## Non-goals
`A(Lrow, Lcol)` 2-mask; `logical()` builtin catalog.
