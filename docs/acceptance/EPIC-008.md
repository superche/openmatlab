# Acceptance evidence — Epic #8 (#115)

**Epic:** [#115 Indexed array assignment](https://github.com/superche/openmatlab/issues/115)  
**Scope issues:** [#116](https://github.com/superche/openmatlab/issues/116) · [#117](https://github.com/superche/openmatlab/issues/117) · absorbs [#111](https://github.com/superche/openmatlab/issues/111)  
**Functional tip** (step 1, PR #118): `7b9a5a33fc98797c0ab42f1259df30b2e0f614ce`  
**Evidence merge tip** (EPIC-008 + sync merged, PR #123): `8ebaaa3d0115712b69b7f9235edaaf524599d4b5`  
**Captured:** 2026-10-11 18:52 CST on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Verdict

**Ready for user acceptance.** `A(i,j)=v` and linear `A(k)=v` green with COW `set_index`. Residual #111 closed as delivered. Tests were **not** weakened.

## Traceability

| Step | Issue | PR | Merge commit | CI `test` |
|------|-------|-----|--------------|-----------|
| 1 | #116 array assign | [#118](https://github.com/superche/openmatlab/pull/118) | `7b9a5a33fc98797c0ab42f1259df30b2e0f614ce` | pass |
| 2–4 | #117 sync + EPIC-008 | [#123](https://github.com/superche/openmatlab/pull/123) | `8ebaaa3d0115712b69b7f9235edaaf524599d4b5` | pass |

## Feature map

`lang.array_assign`, `numerics.array_set` → **done** per `docs/design/ITER-117-epic8-done-criteria.md`.
Counts: **done=41, partial=9, stub=2**.

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
206 passed, 2 deselected
```

## Smoke — CLI transcripts (functional tip `7b9a5a3`)

```text
$ openmatlab -e "A = [1 2; 3 4]; A(2,1) = 9; x = A(2,1)"
x =

9

$ openmatlab -e "v = [1 2 3]; v(2) = 5; y = v(2)"
y =

5

$ openmatlab -e "A = [1 2; 3 4]; A(2) = 8; z = A(2)"
z =

8
```

## Residual (canonical Issues — PROCESS § Residual Issues)

| Residual | Issue |
|----------|-------|
| Grow on OOB assign | [#119](https://github.com/superche/openmatlab/issues/119) |
| `A(i)=[]` delete | [#120](https://github.com/superche/openmatlab/issues/120) |
| Range/logical LHS assign | [#121](https://github.com/superche/openmatlab/issues/121) |
| Non-scalar RHS expand | [#122](https://github.com/superche/openmatlab/issues/122) |

## How to re-run

```bash
git checkout 8ebaaa3d0115712b69b7f9235edaaf524599d4b5   # evidence tip (functional: `7b9a5a33fc98797c0ab42f1259df30b2e0f614ce`)
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab -e "A = [1 2; 3 4]; A(2,1) = 9; x = A(2,1)"
```
