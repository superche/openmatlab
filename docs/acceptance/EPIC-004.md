# Acceptance evidence — Epic #4 (#43)

**Epic:** [#43 Core numeric builtins toolbox](https://github.com/superche/openmatlab/issues/43)  
**Scope issues:** [#44](https://github.com/superche/openmatlab/issues/44) · [#45](https://github.com/superche/openmatlab/issues/45) · [#46](https://github.com/superche/openmatlab/issues/46) · [#47](https://github.com/superche/openmatlab/issues/47) · bugs found en route [#48](https://github.com/superche/openmatlab/issues/48) · [#51](https://github.com/superche/openmatlab/issues/51)  
**Functional tip** (ordered steps 1–3 code complete, PR #52): `ba43aa8138bdc1baf9873d3853900b5f3c319641`  
**Evidence merge tip** (EPIC-004 + sync merged, PR #53): `ea4c140e2da3dd6bb46402b8e7ca99794b7cea4e` — also carries the small error-prefix dedupe fix from review  
**Captured:** 2026-10-11 17:49 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Verdict

**Ready for user acceptance.** Ordered steps 1–5 green. Two pre-existing MATLAB-semantics defects (#48 linear indexing, #51 `[a -b]` literals) were exposed by MATLAB-correct tests and fixed in code — no test weakened.

## Traceability

| Step | Issue | PR | Merge commit | CI `test` |
|------|-------|-----|--------------|-----------|
| 1 | #44 constructors + shape (+ fixes #48) | [#49](https://github.com/superche/openmatlab/pull/49) | `329ab34ad6dc592473dd7988fec1612feac3369b` | pass |
| 2 | #45 reductions | [#50](https://github.com/superche/openmatlab/pull/50) | `9bd34bf9d44c296f1326f0ee3a5843748001af0a` | pass |
| 3 | #46 elfun (+ fixes #51) | [#52](https://github.com/superche/openmatlab/pull/52) | `ba43aa8138bdc1baf9873d3853900b5f3c319641` | pass |
| 4–5 | #47 sync + criteria + EPIC-004 | [#53](https://github.com/superche/openmatlab/pull/53) | `ea4c140e2da3dd6bb46402b8e7ca99794b7cea4e` | pass |

## Feature map

New `libs.elmat_constructors`, `libs.elmat_shape`, `libs.reductions`, `libs.elfun` → **done** per
`docs/design/ITER-047-epic4-done-criteria.md`. Counts after this PR: **done=29, partial=9, stub=2** (was done=25 at Epic #3).

## Measurable gate — pytest

At functional tip `ba43aa8`:

```text
$ pytest -m "unit or bdd" --tb=no
144 passed, 2 deselected in 0.91s
```

After this PR (adds error-message dedupe test): **145 passed, 2 deselected**.

## Smoke — CLI transcripts (functional tip `ba43aa8`)

```text
$ openmatlab -e "A = eye(2, 3)"
A =

[[1. 0. 0.]
 [0. 1. 0.]]

$ openmatlab -e "[m, n] = size(zeros(4, 5))"
m =

4

n =

5

$ openmatlab -e "x = linspace(0, 1, 5)"
x =

[[0.   0.25 0.5  0.75 1.  ]]

$ openmatlab -e "s = sum([1 2; 3 4])"
s =

[[4. 6.]]

$ openmatlab -e "[v, i] = max([3 9 2 9])"
v =

9

i =

2

$ openmatlab -e "r = round([2.5 -2.5])"
r =

[[ 3. -3.]]

$ openmatlab -e "k = mod(-5, 3)"
k =

1

$ openmatlab -e 'w = which("sum")'
w =

builtin/sum
```

Real-domain error — functional tip showed a duplicated prefix (`error: sqrt: sqrt: negative input …`); fixed in this PR (adversarial-review finding):

```text
$ openmatlab -e "q = sqrt(-1)"
error: sqrt: negative input needs complex results (not supported)
```

## Residual (explicit non-goals)

MATLAB NaN-omit default for `max/min` (NumPy propagation today), `'omitnan'`/`'all'` flags, complex results,
integer classes, `zeros([m n])` vector form, `cumsum/sort/find`, N-D arrays, single-quote char + cells (backlog axis).

## How to re-run

```bash
git checkout ea4c140e2da3dd6bb46402b8e7ca99794b7cea4e   # evidence merge tip (or main)
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab -e "[v, i] = max([3 9 2 9])"
```

Functional-only tree (no EPIC-004 yet): `ba43aa8138bdc1baf9873d3853900b5f3c319641`.
