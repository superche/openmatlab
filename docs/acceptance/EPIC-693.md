# Acceptance evidence: Epic #693 (T-E3 table utilities, sorting and sets)

**Epic:** [#693](https://github.com/superche/openmatlab/issues/693)  
**Feature PR:** [#739](https://github.com/superche/openmatlab/pull/739) (#693, #693, #738)  
**Milestone:** [Tables and data types (M10)](https://github.com/superche/openmatlab/milestone/10) · [`docs/milestones/M10-tables.md`](../milestones/M10-tables.md)  
**Design + adversarial review:** [`docs/design/EPIC-693-table-utilities.md`](../design/EPIC-693-table-utilities.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `78763f3bd7e30ba7852afdb7aec6e7452ab89643` | Squash merge of feature PR [#739](https://github.com/superche/openmatlab/pull/739) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M10 criterion T03 is **met**. Epic #693 stays **open** until the user accepts it.

T03 and T05 are both met by this epic (the T05 gate is in the targeted run below). The table/string set-ops part of #585 is absorbed by reference; #585 stays on the Core backlog, untouched.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| T03 conversions, head/tail, varfun/rowfun, variable management, summary | #693 | [#739](https://github.com/superche/openmatlab/pull/739) | [job 116821814340](https://github.com/superche/openmatlab/actions/runs/38854174752/job/116821814340) **success** |
| T05 sortrows/issortedrows, unique/ismember on tables, sort/ismember on categorical | #693 | [#739](https://github.com/superche/openmatlab/pull/739) | same job |
| residual | #738 | [#739](https://github.com/superche/openmatlab/pull/739) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "T = table([3;1;2;1], {'c';'a';'b';'d'}, 'VariableNames', {'n','s'}); S = sortrows(T, {'n','s'}, {'ascend','descend'})"
S =

  4×2 table

    n      s
    _      _

    1    {'d'}
    1    {'a'}
    2    {'b'}
    3    {'c'}
$ openmatlab -e "T = table([1;2;3], [4;5;6], 'VariableNames', {'a','b'}); V = varfun(@sum, T)"
V =

  1×2 table

    sum_a    sum_b
    _____    _____

        6       15
$ openmatlab -e "T = table([1;2;3], [4;5;6], 'VariableNames', {'a','b'}); R = rowfun(@(x, y) x + y, T, 'OutputVariableNames', 'total')"
R =

  3×1 table

    total
    _____

        5
        7
        9
$ openmatlab -e "T = table([1;2;NaN], categorical({'p';'q';'p'}), 'VariableNames', {'n','c'}); summary(T)"
Variables:

    n: 3×1 double

        Values:

            Min             1
            Median        1.5
            Max             2
            NumMissing      1

    c: 3×1 categorical

        Values:

            p    2
            q    1
$ openmatlab -e "[C, ia, ic] = unique(table([1;1;2], [5;5;6]))"
C =

  2×2 table

    Var1    Var2
    ____    ____

       1       5
       2       6

ia =

   1
   3

ic =

   1
   1
   2
$ openmatlab -e "T = table([1;2], {'a';'b'}); table2array(T)"
error: Unable to concatenate the table variables in a single array: the variables have incompatible types.
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1703 passed, 2 deselected, 5 xfailed in 19.27s
$ pytest tests/unit/test_table_utils.py tests/bdd/test_table_utils_bdd.py "tests/conformance/test_m10_conformance.py::test_m10_criterion[T05-m10_t05_sortrows_sets]" "tests/conformance/test_m10_conformance.py::test_m10_criterion[T03-m10_t03_table_conversion_varfun]" --tb=no
33 passed in 0.43s
$ pytest tests/conformance/test_m10_conformance.py --tb=no
8 passed, 3 xfailed in 0.40s
```

New cases: `tests/unit/test_table_utils.py` (27), `tests/bdd/test_table_utils_bdd.py` (4), M10 T03 and T05 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.table_utils
libs.table_utils                 libs       done     table utilities — conversions, head/tail, varfun/rowfun, variable management, summary, sortrows/unique/ismember on tables
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| grouped varfun/rowfun, summary struct output and modern layout, MissingPlacement, unique 'stable' and set ops on tables, anonymous multi-output in rowfun | [#738](https://github.com/superche/openmatlab/issues/738) |

## Milestone progress (M10)

- Criteria met: **7 / 10** (T01, T02, T03, T04, T05, T08, T09)
- Conformance scripts passing: **7 / 10** (strict xfail pending: T06, T07, T10)
- Next: T-E6 #696 (joins and grouping), interleaved with D-E5 #702.
