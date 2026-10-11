# EPIC-021 — Grow-on-assign A(i)= / c{i}= (M2 C08)

**Epic:** [#253](https://github.com/superche/openmatlab/issues/253) · Absorbs [#119](https://github.com/superche/openmatlab/issues/119) [#108](https://github.com/superche/openmatlab/issues/108)

## Dual tips

| Tip | SHA | PR |
|-----|-----|----|
| Functional | `6aadd4289d614dc0884896d82d30f2c95f6a51a5` | [#256](https://github.com/superche/openmatlab/pull/256) |
| Evidence | `13aa9974c790a3640253e5299670d5c39b2beb6a` | [#257](https://github.com/superche/openmatlab/pull/257) |

## Acceptance

1. `v=[1 2]; v(4)=7` → `[1 2 0 7]` (C08) — **PASS**
2. Matrix 2-sub + cell `c{k}=` grow — **PASS**
3. feature_map / catalog / M2 C08 → **met** — **PASS**
4. Residual Issues filed — **PASS**

## Milestone progress

| Milestone | Met | Total | This epic |
|-----------|-----|-------|-----------|
| Octave-breadth (#2) | **9** | 11 | C08 grow-on-assign |

**Conformance:** `c08_grow_on_assign` now met. Remaining: **C09** unique/issorted, **C10** cellfun.

**Gap list:** C09 (p1), C10 (p1); residual grow edge cases below.

## Residual Issues

- https://github.com/superche/openmatlab/issues/258 (p1) matrix linear grow edges
- https://github.com/superche/openmatlab/issues/259 (p2) N-D grow
- https://github.com/superche/openmatlab/issues/260 (p1) cell paren grow


## Tests

286 passed, 2 xfailed (C09/C10). OOB tests rewritten to assert grow (requirement delivery of #119/#108, not silent weaken).
