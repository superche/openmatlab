# Acceptance evidence: Epic #692 (T-E2 categorical)

**Epic:** [#692](https://github.com/superche/openmatlab/issues/692)  
**Feature PR:** [#718](https://github.com/superche/openmatlab/pull/718) (#692, #717)  
**Milestone:** [Tables and data types (M10)](https://github.com/superche/openmatlab/milestone/10) · [`docs/milestones/M10-tables.md`](../milestones/M10-tables.md)  
**Design + adversarial review:** [`docs/design/EPIC-692-categorical.md`](../design/EPIC-692-categorical.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `abdcfdf1dd6f3d8cacb684a8424a42f1f8e34c6a` | Squash merge of feature PR [#718](https://github.com/superche/openmatlab/pull/718) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M10 criterion T04 is **met**. Epic #692 stays **open** until the user accepts it.

T04 is met by this epic. Storage is a native integer code array plus ordered categories (no pandas).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| T04 categorical construction / methods / comparisons / table variable | #692 | [#718](https://github.com/superche/openmatlab/pull/718) | [job 116802253297](https://github.com/superche/openmatlab/actions/runs/38847832265/job/116802253297) **success** |
| residual | #717 | [#718](https://github.com/superche/openmatlab/pull/718) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "c = categorical({'r','g','r','b'}), categories(c)', countcats(c)"
c =

  1×4 categorical array

     r      g      r      b 


ans =

{1×3 cell}
  (1,1) = b
  (1,2) = g
  (1,3) = r

ans =

   1   1   2
$ openmatlab -e "o = categorical({'lo','hi','mid'}, {'lo','mid','hi'}, 'Ordinal', true); o > 'lo'"
ans =

   0   1   1
$ openmatlab -e "T = table(categorical({'a';'b';'a'}), [1;2;3], 'VariableNames', {'g','x'}); T(T.g == 'a', :)"
ans =

  2×2 table

    g    x
    _    _

    a    1
    a    3
$ openmatlab -e "c = categorical({'a'}); c < 'a'"
error: Relational comparisons are not allowed for categorical arrays that are not ordinal.
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1587 passed, 2 deselected, 12 xfailed in 18.10s
$ pytest tests/unit/test_categorical.py tests/bdd/test_categorical_bdd.py "tests/conformance/test_m10_conformance.py::test_m10_criterion[T04-m10_t04_categorical]" --tb=no
21 passed in 0.40s
$ pytest tests/conformance/test_m10_conformance.py --tb=no
4 passed, 7 xfailed in 0.38s
```

New cases: `tests/unit/test_categorical.py` (17), `tests/bdd/test_categorical_bdd.py` (3), M10 T04 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F runtime.categorical
runtime.categorical              runtime    done     categorical type and methods; categorical table variables
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| N-D categorical, scalar display header, logical valueset, protected concat, summary layout | [#717](https://github.com/superche/openmatlab/issues/717) |

## Milestone progress (M10)

- Criteria met: **3 / 10** (T01, T02, T04)
- Conformance scripts passing: **3 / 10** (strict xfail pending: T03, T05, T06, T07, T08, T09, T10)
- Next: T-E4 #694 (readtable/writetable), then D-E4 #701.
