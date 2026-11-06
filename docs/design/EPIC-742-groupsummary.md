# groupsummary empty groups (M17 slice of #742)

Milestone: M17 Analyst pipeline (parent epic #1032). The rest of #742 is on the Core backlog: #1052, #1053, #1054, #1055, #1056.

## Problem

The analyst story groups a cleaned table and needs groups that the rows never mention: a categorical level that was declared but unused, or a combination of grouping values that does not occur. `groupsummary` already aggregated observed groups. `'IncludeEmptyGroups',true` was an error.

## Design

`libs/table_join_group.py` still owns `groupsummary`. The flag is accepted only there. `groupcounts` still raises `groupcounts: 'IncludeEmptyGroups' is not supported yet.`

With the flag on, the output groups are the Cartesian product of each grouping variable's possible values, merged with any missing groups, in the same order as the default path (column by column, missing last inside that column):

- A categorical contributes every category, in category order, including ones with no rows. `<undefined>` is not a category.
- A logical contributes `false` and `true`.
- Anything else contributes the non-missing values that actually occur.
- A row whose grouping value is missing stays in its own group when `'IncludeMissingGroups'` is true (the default), and is dropped when it is false. The group is sorted with the others: column by column, missing last inside that column. It is not moved after every complete group. Empty groups are not invented for a missing value that never occurs.
- For these two functions, a missing text key is whatever `ismissing` reports (#1060). Cellstr `''` is missing. String `<missing>` is missing. String `""` is a real key and sorts with the other strings. A cell containing `' '` is a real key. Char blanks are not adjusted here (#1058). `findgroups` still ranks with `rank_columns` and does not take this path (#1054). `groupcounts` uses the same ranks, so the same flag drops or keeps the empty cellstr group.

`GroupCount` is the number of rows in the group, including rows whose data is NaN. Named methods omit NaN. An empty group therefore has count 0, `sum` 0, and `mean` / `min` / `max` / `std` NaN. The story methods are the ones already implemented: `mean`, `sum`, `min`, `max`, `std`, plus `GroupCount`. There is no `numel` method.

Columns stay in the existing order: grouping variables, `GroupCount`, then for each data variable the methods in the order given (`mean_x`, `sum_x`, `mean_y`, `sum_y`). A single function handle is still `fun1_<var>`.

A bad flag and an unknown method raise `EvalError`. A 0-row numeric table has no groups. A 0-row categorical with the flag on returns one row per category. Group bins, array input, `'VariableNamingRule'`, and a multi-column grouping variable are #1053 (`docs/design/EPIC-1053-groupsummary.md`). `'IncludedEdge'` without bins is still an error.

One existing assertion had to move. `test_errors_are_matlab_errors` listed `IncludeEmptyGroups', true` on a plain numeric group variable, which used to be the unsupported error. MATLAB accepts that call and adds no rows. The success result is `test_plain_numeric_group_adds_no_rows`. No other existing expected value changed.

## Non-goals

`groupcounts` empty groups. `grouptransform` / `groupfilter`. `findgroups` missing-group options. `splitapply` of a table-valued function. Join key options. Char-matrix blanks as missing group keys (#1058). The #1053 slice (bins, array input, `'VariableNamingRule'`, multi-output methods) is `docs/design/EPIC-1053-groupsummary.md`.
