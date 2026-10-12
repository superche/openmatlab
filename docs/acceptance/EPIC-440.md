# Acceptance evidence — Epic #440 (N-D arrays)

**Epic:** [#440 Epic: N-D arrays (ndim > 2)](https://github.com/superche/openmatlab/issues/440)  
**Scope issues (closed by PR #441):** [#74](https://github.com/superche/openmatlab/issues/74) · [#182](https://github.com/superche/openmatlab/issues/182) · [#330](https://github.com/superche/openmatlab/issues/330) · [#173](https://github.com/superche/openmatlab/issues/173) · [#259](https://github.com/superche/openmatlab/issues/259) · [#322](https://github.com/superche/openmatlab/issues/322)  
**Milestone:** [Octave-breadth language & numerics (M2)](https://github.com/superche/openmatlab/milestone/2) · [`docs/milestones/M2-octave-breadth.md`](../milestones/M2-octave-breadth.md)  
**Design + adversarial review:** [`docs/design/EPIC-440-nd-arrays.md`](../design/EPIC-440-nd-arrays.md)  
**Captured:** 2026-10-12 ~22:11 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `3296b5ed19f68fb253052a3c47b9117513c80876` | Squash merge of [#441](https://github.com/superche/openmatlab/pull/441) |
| Evidence merge tip | recorded in the after-epic sync chore (the squash merge of this doc's PR) | Re-run from `main` |

## Verdict

**Ready for user acceptance.** All six scope issues are closed on `main`. M2 criterion C12 is **met**. The epic issue #440 stays **open** until the user accepts it.

## Traceability — Issues → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| N-D core: index/assign/reduce/display | #74 | [#441](https://github.com/superche/openmatlab/pull/441) | [job 114850713226](https://github.com/superche/openmatlab/actions/runs/38260867685/job/114850713226) **success** |
| `zeros/ones/nan/Inf([m n p])`, `(m,n,p)` | #182 | #441 | same |
| `true/false(m,n,p)` | #330 | #441 | same |
| `end` per dim + trailing-dim folding | #173 | #441 | same |
| grow N-D on assign | #259 | #441 | same |
| N-D logical masks | #322 | #441 | same |

## Functional demo (real CLI output)

```text
$ openmatlab -e "A = reshape(1:8, 2, 2, 2)"
A(:,:,1) =

   1   3
   2   4

A(:,:,2) =

   5   7
   6   8

$ openmatlab -e "A = zeros(2,3,4); s = size(A), n = ndims(A)"
s =

   2   3   4

n =

3

$ openmatlab -e "A = reshape(1:8,2,2,2); x = A(2,1,2), e = A(end,end,end), f = A(1,end)"
x =

6

e =

8

f =

7

$ openmatlab -e "B = ones(2); B(:,:,3) = 5; s = size(B), S = sum(B, 3)"
s =

   2   2   3

S =

   6   6
   6   6

$ openmatlab -e "A = reshape(1:8,2,2,2); m = A(A > 6)', t = size(true(2,2,2))"
m =

   7   8

t =

   2   2   2

$ openmatlab -e "A = reshape(1:8,2,2,2); A(1,5) = 1"
error: array assign: Attempt to grow array along ambiguous dimension.
```

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
663 passed, 2 deselected in 2.37s
$ pytest tests/conformance --tb=no
19 passed in 0.41s
$ pytest tests/unit/test_nd_arrays.py tests/bdd/test_nd_arrays_bdd.py "tests/conformance/test_m2_conformance.py::test_m2_criterion[C12-c12_nd_arrays]"
31 passed in 0.44s
```

New cases: 25 unit (`tests/unit/test_nd_arrays.py`), 5 Gherkin scenarios
(`features/nd_arrays.feature`), and conformance `c12_nd_arrays`.

**Test change (contradicted documented MATLAB):** `tests/unit/test_elmat_size_vector.py::test_nd_size_vector_errors`
asserted that `zeros([2 3 4])` raises. That error was an old deferral; MATLAB returns a 2x3x4 array.
The test is now `test_nd_size_vector_builds_nd` and asserts shape `(2, 3, 4)`. No other tests changed.

## Feature map (epic-related)

```text
$ openmatlab features --layer numerics | rg nd_arrays
numerics.nd_arrays               numerics   partial  N-D arrays (ndim > 2): construct, index, assign, reduce, display
```

Status is `partial`, not `done`, because of the residuals below (permute, N-D in `[ ]`, N-D cells).

## Milestone progress (M2)

- Criteria met: **12 / 12** (C12 N-D arrays added at p2 and met by this epic)
- Conformance scripts passing: **12 / 12** (xfail pending: none)
- Remaining gaps (priority order): complex numbers #71 #229 (next epic) · integer/string classes #72 #78 #183 · N-D residuals #442–#446

## Residuals (filed, same milestone)

| Issue | Residual |
|-------|----------|
| [#442](https://github.com/superche/openmatlab/issues/442) | `permute` / `ipermute` |
| [#443](https://github.com/superche/openmatlab/issues/443) | N-D operands in `[ ]` concatenation |
| [#444](https://github.com/superche/openmatlab/issues/444) | N-D cell arrays |
| [#445](https://github.com/superche/openmatlab/issues/445) | flip/circshift/sort/cumsum along dim ≥ 3 coverage |
| [#446](https://github.com/superche/openmatlab/issues/446) | MATLAB "Index in position k exceeds array bounds" wording |
