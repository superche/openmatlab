# Design: logical-mask delete coverage (Issue #307)

**Epic:** #306 · Absorbs #249

## Decision
Path already in `NumpyArrayBackend.set_index` (empty RHS + logical mask). This epic:
1. Unit + BDD coverage for vector expr/mask and matrix→column.
2. Thicken C06 conformance with `v2(v2>2)=[]`.
3. Feature id `runtime.logical_delete`.

## Non-goals
`A(Lrow,Lcol)=[]`; cell logical delete.
