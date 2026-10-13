# Acceptance evidence — Epic #496 (linear solve `\` and `/`)

**Epic:** [#496 Epic: linear solve \ and / (mldivide/mrdivide), inv/det/rank/pinv](https://github.com/superche/openmatlab/issues/496)  
**Feature PR:** [#497](https://github.com/superche/openmatlab/pull/497)  
**Milestone:** [Octave-breadth language & numerics (M2)](https://github.com/superche/openmatlab/milestone/2) · [`docs/milestones/M2-octave-breadth.md`](../milestones/M2-octave-breadth.md)  
**Design + adversarial review:** [`docs/design/EPIC-496-linear-solve.md`](../design/EPIC-496-linear-solve.md)  
**Captured:** 2026-10-13 ~10:00 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `91298ec64bd73d33e0b36fe77843b9daa6ef20f4` | Squash merge of feature PR [#497](https://github.com/superche/openmatlab/pull/497) |
| Evidence merge tip | _recorded by the after-epic sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M2 criterion C17 is **met**. Epic #496 stays **open** until the user accepts it.

**Behaviour fix:** before this epic, matrix `/` divided element-wise (`[1 2;3 4]/[1 2;3 4]` returned all ones) and `\` raised "Unknown binary op". Both now follow the MATLAB mldivide/mrdivide docs.

**Caveat:** the singular case gives Inf/NaN plus MATLAB's warning. The exact Inf/NaN pattern comes from our own pivoted elimination and may differ from LAPACK's in individual entries.

## Traceability — Scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| `A\b`, `B/A` (scalar, square LU, least squares basic solution), `.\`, singular/RCOND/rank-deficient warnings, `warning`/`lastwarn`, `inv`/`det`/`rank`/`pinv`, `mldivide`/`mrdivide` builtins | #496 | [#497](https://github.com/superche/openmatlab/pull/497) | [job 115092616459](https://github.com/superche/openmatlab/actions/runs/38334885468/job/115092616459) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e 'x = [4 -2 1; 3 6 -4; 2 1 8] \ [12; -25; 32]'
x =

    1
   -2
    4

$ openmatlab -e 'y = [1 2; 3 4] / [1 2; 3 4]'
y =

   1   0
   0   1

$ openmatlab -e 'x = [1 1; 1 2; 1 3] \ [1; 2; 2]'
x =

   0.6667
   0.5000

$ openmatlab -e 'x = [1 2 3] \ 6'
x =

   0
   0
   2

$ openmatlab -e 'x = [1 1; 1 1; 1 1] \ [1; 2; 3]'
Warning: Rank deficient, rank = 1, tol = 1.153778e-15.
x =

   2
   0

$ openmatlab -e 'x = [1 2; 2 4] \ [1; 2]'
Warning: Matrix is singular to working precision.
x =

   NaN
   NaN

$ openmatlab -e 'X = inv([1 2; 3 4]), d = det([1 2; 3 4]), r = rank([1 2; 2 4])'
X =

   -2.0000    1.0000
    1.5000   -0.5000

d =

-2.0000

r =

1

$ openmatlab -e 'x = [1 2] \ [1; 2]'
error: Matrix dimensions must agree.
```

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
997 passed, 2 deselected in 3.00s
$ pytest tests/conformance --tb=no
24 passed in 0.44s
$ pytest tests/unit/test_linear_solve.py tests/bdd/test_linear_solve_bdd.py "tests/conformance/test_m2_conformance.py::test_m2_criterion[C17-c17_linear_solve]"
15 passed in 0.43s
```

New cases: 11 unit (`tests/unit/test_linear_solve.py`), 3 Gherkin scenarios
(`features/linear_solve.feature`), and conformance `c17_linear_solve`.

**Existing tests changed: none.** No existing test depended on element-wise matrix `/`.

## Feature map (epic-related)

```text
$ openmatlab features | rg linear_solve
numerics.linear_solve            numerics   done     linear solve mldivide/mrdivide, inv/det/rank/pinv
```

## Residuals (filed)

- [#498](https://github.com/superche/openmatlab/issues/498): `norm`/`cond`/`rcond`/`magic`, `strncmp`, warning identifiers and per-id state, special triangular/Hermitian solvers.
- [#488](https://github.com/superche/openmatlab/issues/488): sparse solvers can now build on this `\` (`S\b` already returns the full solution).

## Milestone progress (M2)

- Criteria met: **17 / 17** (C17 added at p2 and met by this epic)
- Conformance scripts passing: **17 / 17** (xfail pending: none)
- Remaining gaps (all p2): #488 sparse residuals, #494 text follow-ups, #498 linear-algebra residuals
