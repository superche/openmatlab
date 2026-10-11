# EPIC-022 — unique / issorted (M2 C09)

**Epic:** [#265](https://github.com/superche/openmatlab/issues/265) · Absorbs [#97](https://github.com/superche/openmatlab/issues/97)

## Dual tips

| Tip | SHA | PR |
|-----|-----|----|
| Functional | `35d4306b61d75b7a3111a9a7d21f4fee24c6c7e0` | [#268](https://github.com/superche/openmatlab/pull/268) |
| Evidence | `0d59e76301dc3efe6c087a0b67dc56ee5c491d7a` | [#272](https://github.com/superche/openmatlab/pull/272) |

## Acceptance

1. `unique([3 1 3 2])` → `[1 2 3]`; `issorted([1 2 2 5])` → 1 (C09) — **PASS**
2. feature_map / catalog / M2 C09 → **met** — **PASS**
3. Residual Issues filed — **PASS**

## Milestone progress

| Milestone | Met | Total | This epic |
|-----------|-----|-------|-----------|
| Octave-breadth (#2) | **10** | 11 | C09 unique/issorted |

**Conformance:** `c09_unique_issorted` now met. Remaining: **C10** cellfun.

**Gap list:** C10 (p1); residual unique/issorted edges below.

## Residual Issues

- https://github.com/superche/openmatlab/issues/269 (p1) unique index outputs
- https://github.com/superche/openmatlab/issues/270 (p2) 'rows' flags
- https://github.com/superche/openmatlab/issues/271 (p1) issorted matrix / descend

## Tests

292 passed, 1 xfailed (C10). Never weakened.
