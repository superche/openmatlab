# Acceptance evidence: Epic #696 (T-E6 joins and grouping)

**Epic:** [#696](https://github.com/superche/openmatlab/issues/696)  
**Feature PR:** [#744](https://github.com/superche/openmatlab/pull/744) (#696, #696, #742, #743)  
**Milestone:** [Tables and data types (M10)](https://github.com/superche/openmatlab/milestone/10) · [`docs/milestones/M10-tables.md`](../milestones/M10-tables.md)  
**Design + adversarial review:** [`docs/design/EPIC-696-joins-grouping.md`](../design/EPIC-696-joins-grouping.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `1dc5892cafeddddc7d458bb1b5ffa1552efd1dd2` | Squash merge of feature PR [#744](https://github.com/superche/openmatlab/pull/744) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M10 criterion T06 is **met**. Epic #696 stays **open** until the user accepts it.

T06 and T07 are both met by this epic (the T07 gate is in the targeted run below).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| T06 join, innerjoin, outerjoin | #696 | [#744](https://github.com/superche/openmatlab/pull/744) | [job 116825279413](https://github.com/superche/openmatlab/actions/runs/38855295979/job/116825279413) **success** |
| T07 findgroups, splitapply, groupsummary, groupcounts | #696 | [#744](https://github.com/superche/openmatlab/pull/744) | same job |
| residual | #742 | [#744](https://github.com/superche/openmatlab/pull/744) | same job |
| unrelated core bug found while probing | #743 | [#744](https://github.com/superche/openmatlab/pull/744) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "A = table([1;2;3], [10;20;30], 'VariableNames', {'k','x'}); B = table([3;1;4], [300;100;400], 'VariableNames', {'k','y'}); O = outerjoin(A, B, 'MergeKeys', true)"
O =

  4×3 table

    k     x      y
    _     _      _

    1     10    100
    2     20    NaN
    3     30    300
    4    NaN    400
$ openmatlab -e "A = table([1;2;3], [10;20;30], 'VariableNames', {'k','x'}); B = table([3;1;4], [300;100;400], 'VariableNames', {'k','y'}); join(A, B)"
error: join: the right table must contain a row for every key value in the left table. Use innerjoin or outerjoin to drop or fill unmatched rows.
$ openmatlab -e "T = table([1;2;1;2;3], [10;20;30;40;50], 'VariableNames', {'g','x'}); S = groupsummary(T, 'g', {'sum','max'}, 'x')"
S =

  3×4 table

    g    GroupCount    sum_x    max_x
    _    __________    _____    _____

    1             2       40       30
    2             2       60       40
    3             1       50       50
$ openmatlab -e "T = table([1;2;1;2;3], [10;20;30;40;50], 'VariableNames', {'g','x'}); C = groupcounts(T, 'g')"
C =

  3×3 table

    g    GroupCount    Percent
    _    __________    _______

    1             2         40
    2             2         40
    3             1         20
$ openmatlab -e "[G, ID] = findgroups({'b';'a';'b'}); splitapply(@numel, [1;2;3], G)'"
ans =

   1   2
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1735 passed, 2 deselected, 3 xfailed in 18.94s
$ pytest tests/unit/test_table_join_group.py tests/bdd/test_table_join_group_bdd.py "tests/conformance/test_m10_conformance.py::test_m10_criterion[T07-m10_t07_grouping]" "tests/conformance/test_m10_conformance.py::test_m10_criterion[T06-m10_t06_joins]" --tb=no
31 passed in 0.45s
$ pytest tests/conformance/test_m10_conformance.py --tb=no
10 passed, 1 xfailed in 0.39s
```

New cases: `tests/unit/test_table_join_group.py` (25), `tests/bdd/test_table_join_group_bdd.py` (4), M10 T06 and T07 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.table_join_group
libs.table_join_group            libs       done     joins and grouping — join, innerjoin, outerjoin, findgroups, splitapply, groupsummary, groupcounts
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| join KeepOneCopy/row-name keys, cross-type key matching, IncludeEmptyGroups, group bins, groupsummary on arrays, grouptransform/groupfilter | [#742](https://github.com/superche/openmatlab/issues/742) |
| char matrix + string internal error (unrelated, Core) | [#743](https://github.com/superche/openmatlab/issues/743) |

## Milestone progress (M10)

- Criteria met: **9 / 10** (T01, T02, T03, T04, T05, T06, T07, T08, T09)
- Conformance scripts passing: **9 / 10** (strict xfail pending: T10)
- Next: D-E5 #702 (variable editor, p1), then T-E7 #697 (timetable, p2 cuttable).
