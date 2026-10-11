# Acceptance evidence — Epic #6 (#87)

**Epic:** [#87 Data builtins: cumsum / sort / find](https://github.com/superche/openmatlab/issues/87)  
**Scope issues:** [#88](https://github.com/superche/openmatlab/issues/88) · [#89](https://github.com/superche/openmatlab/issues/89) · [#90](https://github.com/superche/openmatlab/issues/90) · [#91](https://github.com/superche/openmatlab/issues/91) · absorbs residual [#73](https://github.com/superche/openmatlab/issues/73)  
**Functional tip** (steps 1–3, PR #94): `3ad6df9feb65a91c773b945ba70d107537ccb0f4`  
**Evidence merge tip** (EPIC-006 + sync merged, PR #98): `b8b31cde4e74537d67593c82114e89940050b04d`
**Captured:** 2026-10-11 18:32 CST on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Verdict

**Ready for user acceptance.** Ordered steps 1–5 green. Residual #73 delivered as cumsum/sort/find. Tests were **not** weakened.

## Traceability

| Step | Issue | PR | Merge commit | CI `test` |
|------|-------|-----|--------------|-----------|
| 1 | #88 cumsum | [#92](https://github.com/superche/openmatlab/pull/92) | `b0807f2db4bc476f1bb92a5bdc3ce1c180acc9cb` | pass |
| 2 | #89 sort | [#93](https://github.com/superche/openmatlab/pull/93) | `9e351edcab4e00fb816e20d11d154a69cd3fd5f5` | pass |
| 3 | #90 find | [#94](https://github.com/superche/openmatlab/pull/94) | `3ad6df9feb65a91c773b945ba70d107537ccb0f4` | pass |
| 4–5 | #91 sync + EPIC-006 | [#98](https://github.com/superche/openmatlab/pull/98) | `b8b31cde4e74537d67593c82114e89940050b04d` | pass |

## Feature map

`libs.cumsum`, `libs.sort`, `libs.find` → **done** per `docs/design/ITER-091-epic6-done-criteria.md`.
Counts: **done=37, partial=9, stub=2**.

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
188 passed, 2 deselected
```

## Smoke — CLI transcripts (functional tip `3ad6df9`)

```text
$ openmatlab -e "y = cumsum([1 2 3 4])"
y =

[[ 1.  3.  6. 10.]]

$ openmatlab -e "[B, I] = sort([3 1 2])"
B =

[[1. 2. 3.]]

I =

[[2. 3. 1.]]

$ openmatlab -e "A = [0 2; 3 0]; i = find(A)"
i =

[[2.]
 [3.]]

$ openmatlab -e "[r, c, v] = find([0 2; 3 0])"
r =

[[2.]
 [1.]]

c =

[[1.]
 [2.]]

v =

[[3.]
 [2.]]
```

## Residual (canonical Issues — PROCESS § Residual Issues)

| Residual | Issue |
|----------|-------|
| sort `'descend'` / ComparisonMethod | [#95](https://github.com/superche/openmatlab/issues/95) |
| find `'first'`/`'last'` flags | [#96](https://github.com/superche/openmatlab/issues/96) |
| issorted / unique | [#97](https://github.com/superche/openmatlab/issues/97) |
| N-D / complex / sparse | [#74](https://github.com/superche/openmatlab/issues/74) / [#71](https://github.com/superche/openmatlab/issues/71) |

## How to re-run

```bash
git checkout b8b31cde4e74537d67593c82114e89940050b04d   # evidence tip (functional: `3ad6df9feb65a91c773b945ba70d107537ccb0f4`)
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab -e "[B, I] = sort([3 1 2])"
```
