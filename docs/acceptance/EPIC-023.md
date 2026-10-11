# EPIC-023 — cellfun + @function_handle (M2 C10)

**Epic:** [#275](https://github.com/superche/openmatlab/issues/275) · Absorbs [#81](https://github.com/superche/openmatlab/issues/81)

## Dual tips

| Tip | SHA | PR |
|-----|-----|----|
| Functional | `0f635e3c9511e8108b0389e9d21a7313220e6d32` | [#278](https://github.com/superche/openmatlab/pull/278) |
| Evidence | PENDING | PENDING |

## Acceptance

1. `c={[1 2],[3 4 5],6}; n=cellfun(@numel,c)` → `[2 3 1]` (C10) — **PASS**
2. feature_map / catalog / M2 C10 → **met** — **PASS**
3. Residual Issues filed — **PASS**
4. **M2 11/11 + close readiness** — **PASS** (see below)

## Milestone progress

| Milestone | Met | Total | This epic |
|-----------|-----|-------|-----------|
| Octave-breadth (#2) | **11** | 11 | C10 cellfun (final) |

**Conformance:** all C01–C11 `met`. `pytest tests/conformance -m conformance` → **0 xfail**.

**Gap list:** none for M2 exit criteria. Post-M2 residuals below and prior epic residuals remain on the milestone as p1/p2 (do not block M2 exit).

## M2 close readiness

Exit criteria from `docs/milestones/M2-octave-breadth.md`:

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Conformance suite green (all `met`, 0 xfail) | **READY** |
| 2 | Required feature_ids at `done` | **READY** |
| 3 | No open `p0` Issue on milestone #2 | **READY** (0 open p0) |

**Recommendation:** Milestone [#2 Octave-breadth language & numerics](https://github.com/superche/openmatlab/milestone/2) is **ready to close** after user acceptance of Epic #23. Closing the milestone is a separately approved step (not done by this epic). Open p1/p2 residuals can move to Domain toolboxes (#3) or stay as post-M2 backlog.

## Residual Issues

- https://github.com/superche/openmatlab/issues/279 (p1) UniformOutput false
- https://github.com/superche/openmatlab/issues/280 (p2) anonymous `@(x)`
- https://github.com/superche/openmatlab/issues/281 (p2) char function name

## Tests

297 passed, 0 xfailed. Lexer `@` test updated to expect AT token (requirement delivery of #276, not silent weaken).
