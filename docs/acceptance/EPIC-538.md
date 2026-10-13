# Acceptance evidence: Epic #538 (dense linear algebra decompositions)

**Epic:** [#538](https://github.com/superche/openmatlab/issues/538)  
**Feature PR:** [#599](https://github.com/superche/openmatlab/pull/599) (#560)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-538-linalg-decomp.md`](../design/EPIC-538-linalg-decomp.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `ae3a09de603fd9fa6ab58f1f2eace3d86279c136` | Squash merge of feature PR [#599](https://github.com/superche/openmatlab/pull/599) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M7 criterion C09 is **met**. Epic #538 stays **open** until the user accepts it.

Covered:
- `eig` (values, right/left vectors, `'vector'`, Hermitian ascending, complex pairs);
- `svd` full/economy, `lu` in all output forms, `qr` full/economy/pivoted;
- `chol` with `[R,p]`/`'lower'`/`MATLAB:posdef`;
- `null`/`orth` with MATLAB's rank tolerance, `trace`, `cross`, conjugating `dot`, `sqrtm`.

NumPy only. One existing conformance line changed with explicit user approval (`sort(eig(A))`).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| eig svd lu qr chol null orth trace cross dot | #560 | [#599](https://github.com/superche/openmatlab/pull/599) | [job 115158144131](https://github.com/superche/openmatlab/actions/runs/38355760078/job/115158144131) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "A = [4 1; 2 3]; [V, D] = eig(A); r = norm(A*V - V*D) < 1e-10"
r =

1
$ openmatlab -e "s = svd([3 0; 0 4]), es = eig([2 1; 1 2])"
s =

   4
   3

es =

   1
   3
$ openmatlab -e "[L, U, P] = lu([1 2; 3 4])"
L =

   1.0000   0.0000
   0.3333   1.0000

U =

   3.0000   4.0000
   0.0000   0.6667

P =

   0   1
   1   0
$ openmatlab -e "R = chol([4 2; 2 3]), [R2, p] = chol([1 2; 2 1])"
R =

   2.0000   1.0000
   0.0000   1.4142

R2 =

1

p =

2
$ openmatlab -e "t = trace(magic(3)), c = cross([1 0 0], [0 1 0]), d = dot([1 2 3], [4 5 6])"
t =

15

c =

   0   0   1

d =

32
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1305 passed, 2 deselected, 1 xfailed in 18.32s
$ pytest tests/unit/test_decomp.py tests/bdd/test_decomp_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C09-m7_c09_linalg_decomp]" --tb=no
12 passed in 0.49s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
10 passed, 1 xfailed in 1.33s
```

New cases: 9 unit tests (`tests/unit/test_decomp.py`), 2 Gherkin scenarios (`features/decomp.feature`), and conformance `m7_c09_linalg_decomp` (18 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.linalg_decomp
libs.linalg_decomp               libs       done     dense linear algebra decompositions
```

## Residuals (filed)

- [#598](https://github.com/superche/openmatlab/issues/598) (p2): QZ for singular B, schur/hess/logm/linsolve, sparse decompositions.

## Milestone progress (M7)

- Criteria met: **9 / 10** (C01–C09)
- Conformance scripts passing: **9 / 10** (strict xfail pending: C10)
- Next: Epic #539 (C10 containers.Map and datetime)
