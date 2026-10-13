# Acceptance evidence — Epic #487 (sparse matrices)

**Epic:** [#487 Epic: sparse matrices](https://github.com/superche/openmatlab/issues/487)  
**Scope issue (closed by PR #489):** [#451](https://github.com/superche/openmatlab/issues/451)  
**Milestone:** [Octave-breadth language & numerics (M2)](https://github.com/superche/openmatlab/milestone/2) · [`docs/milestones/M2-octave-breadth.md`](../milestones/M2-octave-breadth.md)  
**Design + adversarial review:** [`docs/design/EPIC-487-sparse.md`](../design/EPIC-487-sparse.md)  
**Captured:** 2026-10-13 ~09:37 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `c49f994c90fa4e90bf1acab3bb97f2ff3955666a` | Squash merge of feature PR [#489](https://github.com/superche/openmatlab/pull/489) |
| Evidence merge tip | *(recorded by the after-epic sync PR)* | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** #451 is closed. M2 criterion C16 is **met**. The epic issue #487 stays **open** until the user accepts it.

**Design caveat (by choice):** sparse is a MATLAB-visible attribute over a dense NumPy buffer, because the project has no SciPy dependency. Memory is O(m*n). Compressed storage is residual #488.

## Traceability — Issues → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| `sparse` (all forms), `full`, `issparse`, `nnz`, `nonzeros`, `nzmax`, `speye`, `spones`; propagation rules; `S^p`; triplet display | #451 | [#489](https://github.com/superche/openmatlab/pull/489) | [job 115086371274](https://github.com/superche/openmatlab/actions/runs/38332879715/job/115086371274) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e 'S = sparse([1 1 2], [1 1 3], [2 3 4]), n = nnz(S)'
S =

   (1,1)    5
   (2,3)    4

n =

2

$ openmatlab -e 'Z = sparse(2, 3)'
Z =

   All zero sparse: 2x3

$ openmatlab -e 'S = speye(2); a = issparse(S * 3), b = issparse(S + 1), P = S ^ 2'
a =

1

b =

0

P =

   (1,1)    1
   (2,2)    1

$ openmatlab -e 'F = full(sparse(2, 1, 7))'
F =

   0
   7

$ openmatlab -e 'x = sparse(int8(1))'
error: sparse: Undefined function 'sparse' for input arguments of type 'int8'.
```

The int8 error message repeats the `sparse:` prefix that builtin errors add. The wording after the prefix is MATLAB's.

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
932 passed, 2 deselected in 2.76s
$ pytest tests/conformance --tb=no
23 passed in 0.46s
$ pytest tests/unit/test_sparse.py tests/bdd/test_sparse_bdd.py "tests/conformance/test_m2_conformance.py::test_m2_criterion[C16-c16_sparse]"
37 passed in 0.48s
```

New cases: 33 unit (`tests/unit/test_sparse.py`), 3 Gherkin scenarios
(`features/sparse.feature`), and conformance `c16_sparse`.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg sparse
numerics.sparse                  numerics   done     sparse matrices (sparse attribute)
```

## Residuals (filed)

- [#488](https://github.com/superche/openmatlab/issues/488): compressed storage, `spdiags`/`sprand`/`spfun`/`spalloc`, sparse solvers (`\` is not implemented yet for any matrix), sparse `for` loop columns, and checking the `S.^0` corner case.

## Milestone progress (M2)

- Criteria met: **16 / 16** (C16 added at p2 and met by this epic)
- Conformance scripts passing: **16 / 16** (xfail pending: none)
- Remaining gaps (priority order, all p2): #479 N-D cell residuals, #480 `eps(x)` relative, #483 string residuals, #488 sparse residuals
