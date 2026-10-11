# EPIC-027 — 2-D logical indexing A(L,:) / A(L1,L2)

**Epic:** [#316](https://github.com/superche/openmatlab/issues/316) · Absorbs [#237](https://github.com/superche/openmatlab/issues/237)

## Dual tips

| Tip | SHA | PR |
|-----|-----|----|
| Functional | `458602e132cf456e64d8ae4779a2e53fe26a2a84` | [#319](https://github.com/superche/openmatlab/pull/319) |
| Evidence | PENDING | PENDING |

## Acceptance

1. `A(L1,:)`, `A(:,L2)`, `A(L1,L2)` read — **PASS**
2. Assign `A(L,:)=v` — **PASS**
3. C07 thickened; close #237; residuals — **PASS**

## Milestone progress

| Milestone | Met | Total | Notes |
|-----------|-----|-------|-------|
| Octave-breadth (#2) | **11** | 11 | M2 **OPEN**; next residual p1 **#238** |

## Residual Issues

- https://github.com/superche/openmatlab/issues/320 (p1) 2-D logical delete
- https://github.com/superche/openmatlab/issues/321 (p1) true/false / logical() (#238)
- https://github.com/superche/openmatlab/issues/322 (p2) N-D logical

## Tests

315 passed, 0 xfailed. Never weakened.
