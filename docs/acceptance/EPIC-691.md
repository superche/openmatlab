# Acceptance evidence: Epic #691 (T-E1 table core)

**Epic:** [#691](https://github.com/superche/openmatlab/issues/691)  
**Feature PR:** [#710](https://github.com/superche/openmatlab/pull/710) (#691, #691, #709)  
**Milestone:** [Tables and data types (M10)](https://github.com/superche/openmatlab/milestone/10) · [`docs/milestones/M10-tables.md`](../milestones/M10-tables.md)  
**Design + adversarial review:** [`docs/design/EPIC-691-table-core.md`](../design/EPIC-691-table-core.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `7d5abec2c23e5b3466db4f232b04ff6fa1895a31` | Squash merge of feature PR [#710](https://github.com/superche/openmatlab/pull/710) |
| Evidence merge tip | `29df0164255df85b5bf626333fed6b39b280d6a7` | Squash merge of [#711](https://github.com/superche/openmatlab/pull/711); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M10 criterion T01 is **met**. Epic #691 stays **open** until the user accepts it.

T01 and T02 are both met by this epic (T02 gate: `test_m10_criterion[T02-m10_t02_table_indexing]` in the targeted run below). Storage is the approved native column store (no pandas).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| T01 construction / Properties / display | #691 | [#710](https://github.com/superche/openmatlab/pull/710) | [job 116796568109](https://github.com/superche/openmatlab/actions/runs/38846003838/job/116796568109) **success** |
| T02 indexing / assignment / concat | #691 | [#710](https://github.com/superche/openmatlab/pull/710) | same job |
| residual | #709 | [#710](https://github.com/superche/openmatlab/pull/710) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "Name = {'Ann';'Bob'}; Age = [31;45]; T = table(Name, Age)"
T =

  2×2 table

      Name     Age
      ____     ___

    {'Ann'}     31
    {'Bob'}     45
$ openmatlab -e "T = table([1;2;3],[4;5;6],'VariableNames',{'a','b'}); T.c = T.a + T.b; T(T.a > 1, :)"
ans =

  2×3 table

    a    b    c
    _    _    _

    2    5    7
    3    6    9
$ openmatlab -e "T = table([1;2]); T.zz"
error: Unrecognized table variable name 'zz'.
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1542 passed, 2 deselected, 16 xfailed in 18.03s
$ pytest tests/unit/test_table_core.py tests/bdd/test_table_core_bdd.py "tests/conformance/test_m10_conformance.py::test_m10_criterion[T02-m10_t02_table_indexing]" "tests/conformance/test_m10_conformance.py::test_m10_criterion[T01-m10_t01_table_construct_display]" --tb=no
27 passed in 0.44s
$ pytest tests/conformance/test_m10_conformance.py --tb=no
3 passed, 8 xfailed in 0.39s
```

New cases: `tests/unit/test_table_core.py` (22), `tests/bdd/test_table_core_bdd.py` (3), M10 T01/T02 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F runtime.table_core
runtime.table_core               runtime    done     table core — construction, Properties, indexing/assignment, concatenation, display
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Size/VariableTypes preallocation, nested tables, display fidelity, uminus naming, Workspace Value column | [#709](https://github.com/superche/openmatlab/issues/709) |

## Milestone progress (M10)

- Criteria met: **2 / 10** (T01, T02)
- Conformance scripts passing: **2 / 10** (strict xfail pending: T03, T04, T05, T06, T07, T08, T09, T10)
- Next: D-E2 #699 (pause-model design doc first), then T-E2 #692 / T-E4 #694.
