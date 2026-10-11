# EPIC-026 — Logical-mask delete A(L)=[] coverage

**Epic:** [#306](https://github.com/superche/openmatlab/issues/306) · Absorbs [#249](https://github.com/superche/openmatlab/issues/249)

## Dual tips

| Tip | SHA | PR |
|-----|-----|----|
| Functional | `f419bc89abfaf084f692cab82abc721508928e8a` | [#309](https://github.com/superche/openmatlab/pull/309) |
| Evidence | PENDING | PENDING |

## Acceptance

1. Vector expr/mask delete tests — **PASS**
2. Matrix → column covered — **PASS**
3. C06 thickened with logical delete — **PASS**
4. Close #249; residuals — **PASS**

## Milestone progress

| Milestone | Met | Total | Notes |
|-----------|-----|-------|-------|
| Octave-breadth (#2) | **11** | 11 | M2 **OPEN**; next residual p1 **#237** |

## Residual Issues

- https://github.com/superche/openmatlab/issues/310 (p1) 2-D logical delete
- https://github.com/superche/openmatlab/issues/311 (p2) cell logical delete
- https://github.com/superche/openmatlab/issues/312 (p2) empty-result edges

## Tests

311 passed, 0 xfailed. Coverage only added — never weakened.
