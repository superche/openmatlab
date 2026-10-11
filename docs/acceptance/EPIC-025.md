# EPIC-025 — Thicken M2 conformance (honesty)

**Epic:** [#296](https://github.com/superche/openmatlab/issues/296)

## Dual tips

| Tip | SHA | PR |
|-----|-----|----|
| Functional | `34e220fd9a64bece0ded80985d629b8f70008b5d` | [#299](https://github.com/superche/openmatlab/pull/299) |
| Evidence | `032d2a7960c2ced65e67328045de72bc2898b768` | [#303](https://github.com/superche/openmatlab/pull/303) |

## Acceptance

1. C04 Inf/pi; C06 cell delete; C08 cell grow; C10 sum/max — **PASS**
2. Conformance green, 0 xfail; Inf/-Inf JSON tokens — **PASS**
3. M2 doc honesty section; residuals — **PASS**

## Milestone progress

| Milestone | Met | Total | Notes |
|-----------|-----|-------|-------|
| Octave-breadth (#2) | **11** | 11 | Exit still hold; suite **deeper**; milestone **OPEN** |

**Conformance:** thickened C04/C06/C08/C10. Status unchanged `met` (stricter asserts still pass).

**Gap list:** further depth residuals below; product residual p1 resumes after acceptance (#249…).

## Residual Issues

- https://github.com/superche/openmatlab/issues/300 (p1) C11 matrix-power depth
- https://github.com/superche/openmatlab/issues/301 (p1) C07 2-D logical depth
- https://github.com/superche/openmatlab/issues/302 (p2) direct cell shape expected

## Tests

307 passed, 0 xfailed. Assertions only added/strengthened — never weakened.
