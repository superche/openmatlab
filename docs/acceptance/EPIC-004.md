# Acceptance evidence — Epic #4 (#43)

**Epic:** [#43 Core numeric builtins toolbox](https://github.com/superche/openmatlab/issues/43)  
**Scope issues:** [#44](https://github.com/superche/openmatlab/issues/44) · [#45](https://github.com/superche/openmatlab/issues/45) · [#46](https://github.com/superche/openmatlab/issues/46) · [#47](https://github.com/superche/openmatlab/issues/47) · bugs [#48](https://github.com/superche/openmatlab/issues/48) · [#51](https://github.com/superche/openmatlab/issues/51) · conditional pass [#55](https://github.com/superche/openmatlab/issues/55)  
**Functional tip** (NaN-omit max/min + nan/NaN, PR #56): `82096934afd55b8c93bc937bf02d2f8dc8672ab7`  
**Evidence merge tip:** *(stamped by follow-up PR after this doc merges)*  
**Captured:** 2026-10-11 17:59 CST on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Verdict

**Ready for user re-acceptance (conditional pass closed).** Ordered steps 1–5 from the epic plus the user-required **max/min default omitnan** (#55) are green. Tests were written to MATLAB defaults and were **not** weakened.

## Traceability

| Step | Issue | PR | Merge commit | CI `test` |
|------|-------|-----|--------------|-----------|
| 1 | #44 constructors + shape (+ #48) | [#49](https://github.com/superche/openmatlab/pull/49) | `329ab34ad6dc592473dd7988fec1612feac3369b` | pass |
| 2 | #45 reductions | [#50](https://github.com/superche/openmatlab/pull/50) | `9bd34bf9d44c296f1326f0ee3a5843748001af0a` | pass |
| 3 | #46 elfun (+ #51) | [#52](https://github.com/superche/openmatlab/pull/52) | `ba43aa8138bdc1baf9873d3853900b5f3c319641` | pass |
| 4–5 | #47 sync + EPIC-004 (initial) | [#53](https://github.com/superche/openmatlab/pull/53) | `ea4c140e2da3dd6bb46402b8e7ca99794b7cea4e` | pass |
| Cond. | #55 max/min omitnan + nan/NaN | [#56](https://github.com/superche/openmatlab/pull/56) | `82096934afd55b8c93bc937bf02d2f8dc8672ab7` | pass |
| Refresh | EPIC-004 dual tips (this) | *(this PR)* | evidence merge tip | required |

## Feature map

`libs.elmat_constructors`, `libs.elmat_shape`, `libs.reductions`, `libs.elfun` → **done** per
`docs/design/ITER-047-epic4-done-criteria.md` (updated for #55 NaN default). Counts: **done=29, partial=9, stub=2**.

## Measurable gate — pytest

At functional tip `8209693`:

```text
$ pytest -m "unit or bdd" --tb=no
152 passed, 2 deselected in 0.76s
```

## Smoke — CLI transcripts (functional tip `8209693`)

```text
$ openmatlab -e "v = max([1 nan() 4])"
v =

4

$ openmatlab -e "[m, i] = max([nan() nan()])"
m =

NDArrayValue(shape=(1, 1))

i =

1

$ openmatlab -e "e = max([1 nan()], [nan() 2])"
e =

[[1. 2.]]

$ openmatlab -e "a = nan(1, 2)"
a =

[[nan nan]]

$ openmatlab -e "s = sum([1 nan() 3])"
s =

NDArrayValue(shape=(1, 1))
```

Note: `sum` still **propagates** NaN (MATLAB default for `sum` — only `max`/`min` default to omitnan).

## Residual (still non-goals — not acceptance blockers)

| Residual | Status |
|----------|--------|
| Explicit `'omitnan'` / `'includenan'` / `'all'` flag strings | **non-goal** (default omitnan is implemented; flags not) |
| `zeros([m n])` vector size form | **non-goal** (scalar `zeros(m,n)` works) |
| Complex results, integer classes | **non-goal** |
| `cumsum` / `sort` / `find` | **non-goal** |
| N-D (>2) arrays | **non-goal** |
| Single-quote char + cell arrays | **backlog** (next epic candidate) |

## How to re-run

```bash
git checkout 82096934afd55b8c93bc937bf02d2f8dc8672ab7   # functional tip; or evidence tip / main after stamp
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab -e "v = max([1 nan() 4])"
```
