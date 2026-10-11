# EPIC-024 — cell paren assign / multi-index delete

**Epic:** [#286](https://github.com/superche/openmatlab/issues/286) · Absorbs [#247](https://github.com/superche/openmatlab/issues/247)

## Dual tips

| Tip | SHA | PR |
|-----|-----|----|
| Functional | `c89e3286bbcf6b72632557a5a7a872a29435b44f` | [#289](https://github.com/superche/openmatlab/pull/289) |
| Evidence | `2e7b09e145ccee34ec2061c5203495e879908907` | [#293](https://github.com/superche/openmatlab/pull/293) |

## Acceptance

1. `c={1,2,3}; c(2)={9}` replaces cell 2 — **PASS**
2. `c(i,j)=[]` multi-index delete — **PASS**
3. Maps; close #247; residuals — **PASS**

## Milestone progress

| Milestone | Met | Total | Notes |
|-----------|-----|-------|-------|
| Octave-breadth (#2) | **11** | 11 | Exit criteria still hold; milestone **LEFT OPEN** (user) |

**Conformance:** unchanged 11/11. This epic is post-exit residual p1 (#247 first in residual order).

**Gap list:** next residual p1 after #247: #249, #237, …

## Residual Issues

- https://github.com/superche/openmatlab/issues/290 (p1) multi-element paren assign
- https://github.com/superche/openmatlab/issues/291 (p2) size/reshape nuances
- https://github.com/superche/openmatlab/issues/292 (p2) non-cell RHS conversion

## Tests

302 passed, 0 xfailed. Never weakened.
