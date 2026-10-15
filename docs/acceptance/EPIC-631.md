# Acceptance evidence: Epic #631 (sparse maturity — results stay sparse, sparse solves)

**Epic:** [#631](https://github.com/superche/openmatlab/issues/631)  
**Feature PR:** [#686](https://github.com/superche/openmatlab/pull/686) (#631, #527)  
**Milestone:** [Domain toolboxes (M3)](https://github.com/superche/openmatlab/milestone/3) · [`docs/milestones/M3-domain-toolboxes.md`](../milestones/M3-domain-toolboxes.md)  
**Design + adversarial review:** [`docs/design/EPIC-631-sparse-maturity.md`](../design/EPIC-631-sparse-maturity.md)  
**Captured:** 2026-10-15 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `a1ef8902bfbc4e1c7a5e6f46619bfd14e6419017` | Squash merge of feature PR [#686](https://github.com/superche/openmatlab/pull/686) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M3 criterion T07 is **met**. Epic #631 stays **open** until the user accepts it.

Covered (core):
- `~S`, `S == 0`, `S <= k` and other mostly-true relational results stay sparse when `m*n ≤ COMPLEMENT_BUDGET`;
- `kron` stays sparse when either factor is sparse;
- arithmetic, transpose, indexing, `sum`, `spones`/`spalloc`/`spdiags` already sparse from prior epics;
- sparse `\\` at n=2000 (tridiagonal) stays accurate without densifying `T`; result is full as in MATLAB.

No existing test or conformance expected file changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| M3-E7 sparse maturity (T07) | #631 | [#686](https://github.com/superche/openmatlab/pull/686) | [job 116518781923](https://github.com/superche/openmatlab/actions/runs/38762968272/job/116518781923) **success** |
| mostly-true results + large solves | #527 | [#686](https://github.com/superche/openmatlab/pull/686) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "S = speye(3); [issparse(S == 0) issparse(~S) issparse(S <= 0.5) nnz(~S)]"
ans =

   1   1   1   6
$ openmatlab -e "A = sparse([4 1 0; 1 4 1; 0 1 4]); [issparse(kron(speye(2), A)) nnz(kron(speye(2), A))]"
ans =

    1   14
$ openmatlab -e "A = sparse([4 1 0; 1 4 1; 0 1 4]); b = [1; 2; 3]; x = A \ b; [issparse(x) norm(A*x - b) < 1e-12]"
ans =

   0   1
$ openmatlab -e "n = 2000; T = spdiags([ones(n, 1) 4*ones(n, 1) ones(n, 1)], -1:1, n, n); yy = T \ ones(n, 1); [issparse(T) abs(yy(1000) - 1/6) < 1e-10 nnz(T)]"
ans =

      1      1   5998
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1489 passed, 2 deselected in 17.22s
$ pytest tests/unit/test_sparse_maturity.py tests/bdd/test_sparse_maturity_bdd.py "tests/conformance/test_m3_conformance.py::test_m3_criterion[T07-m3_t07_sparse]" --tb=no
7 passed in 0.44s
$ pytest tests/conformance/test_m3_conformance.py --tb=no
8 passed in 0.54s
```

New cases: 4 unit tests (`tests/unit/test_sparse_maturity.py`), 2 Gherkin scenarios (`features/sparse_maturity.feature`), and conformance `m3_t07_sparse` (20 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F numerics.sparse_maturity
numerics.sparse_maturity         numerics   done     sparse maturity — mostly-true results, kron, large solves (M3-E7)
```

## Residuals (filed)

- [#685](https://github.com/superche/openmatlab/issues/685) (p2): huge complement representation for `~S`/`S==0`; native RCOND for singular `S\\b`; `S op S` when `op(0,0)` is true.

## Milestone progress (M3)

- Criteria met: **7 / 7** (T01, T02, T03, T04, T05, T06, T07)
- Conformance scripts passing: **7 / 7** (strict xfail pending: none)
- Next: M3 exit — propose close-out when Shaw accepts; residuals remain open
