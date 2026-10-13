# Acceptance evidence — Epic #520 (compressed sparse storage)

**Epic:** [#520 Epic: compressed sparse storage (CSC)](https://github.com/superche/openmatlab/issues/520)  
**Feature PR:** [#521](https://github.com/superche/openmatlab/pull/521) (closes #515, #516, #517)  
**Milestone:** [Octave-breadth language & numerics (M2)](https://github.com/superche/openmatlab/milestone/2) · [`docs/milestones/M2-octave-breadth.md`](../milestones/M2-octave-breadth.md)  
**Design + adversarial review:** [`docs/design/EPIC-520-sparse-csc.md`](../design/EPIC-520-sparse-csc.md)  
**Captured:** 2026-10-13 ~11:10 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `8f5b4941e2e193b58c7844c6f01d2435f370637b` | Squash merge of feature PR [#521](https://github.com/superche/openmatlab/pull/521) |
| Evidence merge tip | `65e4f3ce3963cdf89066c590736b89c1c99739a3` | Squash merge of [#524](https://github.com/superche/openmatlab/pull/524); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M2 criterion C19 is **met**. Epic #520 stays **open** until the user accepts it.

`SparseValue` now holds a CSC-ordered `Store` with O(nnz) memory.
`sparse(1e5,1e5)`, `speye(1e5)`, `S*x`, `S*S`, `S±S`, `sum`, `find`, `S(i,j)`, assignment with growth,
deletion and `[S; S]` all run on 1e5×1e5 matrices with **zero densifications**, checked by
`sparse.DENSIFY_COUNT`. The C19 script also passes under `ulimit -v 1.5 GB`; the dense
buffer would need 80 GB. Every other operation densifies lazily and gives the same results as before.

**Side fix:** `S(:)` used to come back full. It is now sparse, as in MATLAB. No existing test asserted the old class.

## Traceability — Scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| CSC container; `sparse`/`speye`/`spalloc`/`spdiags`/`sprand`/`spones`/`spfun`; `nnz`/`nzmax`/`nonzeros`/`find`/`size`/`full`/display without densifying | #515 | [#521](https://github.com/superche/openmatlab/pull/521) | [job 115109053624](https://github.com/superche/openmatlab/actions/runs/38340141981/job/115109053624) **success** |
| Kernels: `S*X`, `X*S`, `S*S`, `S±S`, `.*`, `./`, `k*S`, `-S`, `S'`, `S.^p`, zero-preserving elementwise functions, `sum`/`max`/`min`; randomized and `sprand` parity | #516 | [#521](https://github.com/superche/openmatlab/pull/521) | same job |
| `S(i,j)`, `S(k)`, `S(mask)`, `S(:)`, assignment with growth, deletion, concatenation; randomized parity | #517 | [#521](https://github.com/superche/openmatlab/pull/521) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "S = sparse(100000, 100000); E = speye(100000); n = nnz(E), z = size(S)"
n =

100000

z =

   100000   100000

$ openmatlab -e "S = sparse([1 1 2], [1 1 3], [2 3 4])"
S =

   (1,1)    5
   (2,3)    4

$ openmatlab -e "A = sparse([4 1 0; 1 3 1; 0 1 2]); y = A * [1; 2; 3], c = max(-A)"
y =

    6
   10
    8

c =

   (1,2)    -1

$ openmatlab -e "n = 100000; S = sparse(n, n); S(5, 7) = 3; S(n, n) = 4; S(:, 1) = []; [i, j, v] = find(S)"
i =

        5
   100000

j =

       6
   99999

v =

   3
   4

$ openmatlab -e "S = sparse([1 0 2; 0 3 0]); T = [S; S]; v = T(:)"
v =

   (1,1)     1
   (3,1)     1
   (6,1)     3
   (8,1)     3
   (9,1)     2
   (11,1)    2
```

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
1072 passed, 2 deselected in 7.98s
$ pytest tests/conformance --tb=no
26 passed in 0.52s
$ pytest tests/unit/test_sparse_csc.py tests/bdd/test_sparse_csc_bdd.py "tests/conformance/test_m2_conformance.py::test_m2_criterion[C19-c19_sparse_csc]"
19 passed in 1.06s
$ pytest tests/unit/test_sparse.py tests/unit/test_sparse_residuals.py tests/bdd/test_sparse_bdd.py "tests/conformance/test_m2_conformance.py::test_m2_criterion[C16-c16_sparse]"
44 passed in 0.61s
```

New cases: 15 unit (`tests/unit/test_sparse_csc.py`), 3 Gherkin scenarios
(`features/sparse_csc.feature`), and conformance `c19_sparse_csc`.

**Existing tests changed: none.** `test_sparse.py`, `test_sparse_residuals.py`, `test_sparse_bdd.py` and C16 pass unchanged.

## Feature map (epic-related)

```text
$ openmatlab features | rg sparse
numerics.sparse                  numerics   done     sparse matrices (sparse attribute)
numerics.sparse_csc              numerics   done     compressed sparse storage (CSC)
```

## Residuals (filed)

- [#522](https://github.com/superche/openmatlab/issues/522): native sparse direct solve for `S\b`. Today it densifies, which #517 allows.
- [#523](https://github.com/superche/openmatlab/issues/523): remaining densifying paths: linear `S(:)` colon expansion on huge `S`, relational ops, `mean`/`cumsum`/`reshape`, `S^p`, `for` over columns.

## Milestone progress (M2)

- Criteria met: **19 / 19** (C19 added at p2 and met by this epic)
- Conformance scripts passing: **19 / 19** (xfail pending: none)
- Remaining gaps (all p2): #522, #523
