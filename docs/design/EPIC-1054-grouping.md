# findgroups IncludeMissing, splitapply tables, groupcounts, grouptransform, groupfilter (#1054, #1055)

Milestone: M18 Analysis stack deepen (epic #1063). Residuals of epic #696, moved off #742.

## Problem

`findgroups` numbered only non-missing keys. A NaN, NaT, undefined categorical, or string `<missing>` became NaN in `G` and was left out of `ID` / `TID`. There was no switch to keep that key.

`splitapply` required every output to be one row. A function that returned a table was rejected, so a per-group table could not be stacked.

`groupcounts` accepted only `groupcounts(T, groupvars)`. `'IncludeEmptyGroups', true` raised `groupcounts: 'IncludeEmptyGroups' is not supported yet.` `grouptransform` and `groupfilter` were not implemented.

## What the public docs say

Clean-room only: the MathWorks reference pages for `findgroups`, `splitapply`, `groupcounts`, `grouptransform`, and `groupfilter` (fetched 2026-11-06). No product source.

**findgroups.** The current page does not list a name-value argument. It says missing strings, empty character vectors, `NaN`, `NaT`, and undefined categoricals become `NaN` in `G` and are omitted from the identifiers. That is the default this slice keeps, under the name the issue uses: `'IncludeMissing', false`. `'IncludeMissing', true` gives those keys a group number and returns them in `ID` / `TID`. Ordering is the sort `group_numbers` already uses: column by column, missing last inside that column. A missing second key therefore stays with its first key; it is not moved after every later key. `findgroups` still ranks with `rank_columns`, not the #1060 `ismissing` path, so a cellstr `''` remains a present key. Char blanks stay on #1058.

**splitapply.** The page says outputs are concatenated in group-number order, and an array result has to be one row when the data are columns. A table is not an array row. This slice stacks the tables vertically, in group order, including a table with more than one row. An array that is not one row is still an error. A mix of table and non-table in one output slot is an error. Incompatible table variables raise the existing vertcat error.

**groupcounts.** `B = groupcounts(A)` counts unique rows of a vector, matrix, or cell of column vectors. `[B,BG,BP]` adds the group keys and the percentage of input rows in `[0, 100]`. One grouping vector returns `BG` as that vector; several return a row cell. The table form is unchanged when the new options are off: grouping variables, `GroupCount`, `Percent`, denominator `height(T)`. `'IncludeMissingGroups'` still defaults to true. `'IncludeEmptyGroups'` uses the #742 rule already used by `groupsummary`: every categorical category, both logical values, every bin, and the combinations of those, with a count of 0 and a percent of 0. A plain numeric vector gains no empty rows. Binning is the #1053 set (numeric edges, a positive bin count, `IncludedEdge`, `dayname` / `monthname` / the `*of*` units).

**grouptransform.** One method, applied to each non-grouping variable (or to `datavars`), in the input row order. `'zscore'` is `(x - mean) / std` with the sample standard deviation (`N-1`); a group with fewer than two finite values, or a standard deviation of 0, is NaN. `'norm'` divides by the 2-norm (the published day-name profit example). `'meancenter'` subtracts the mean. `'rescale'` maps the finite range onto `[0, 1]`; a constant group is NaN. Those four omit NaN while computing the statistic and leave NaN entries as NaN. `'meanfill'` replaces NaN with the mean of the finite values. `'linearfill'` is interior linear interpolation along the group's row order; a leading or trailing NaN stays NaN. A function handle may return one row, which is repeated, or one row per group member. `'ReplaceValues', false` appends `<method>_<var>` (a function handle uses `fun1_<var>`). Bins are appended under the #1053 names and do not replace the original grouping column.

**groupfilter.** The method is a function handle. A logical scalar keeps or drops the whole group. A logical vector keeps rows. With more than one data variable, a row is kept only when every variable's result is true. Output rows stay in input order. `[B,BG]` returns the grouping values of the kept rows, not one row per group. The same bin columns are appended before the rows are dropped.

## Design

`libs/table_join_group.py` still owns the functions. `groupcounts`, `grouptransform`, and `groupfilter` build a temporary table and call `_group_table`, so the #742 empty-group product and the #1060 missing-key ranks stay one implementation. `findgroups` calls `group_numbers` directly, as before.

`'IncludeEmptyGroups'` is enabled for `groupcounts` by passing `allow_empty=True`. `grouptransform` and `groupfilter` do not take that flag. They do include a missing key as a group, because the result has one output row per input row (or a subset of those rows) and a row with no group would disappear.

## Non-goals

Timetable row times. `pattern`, `vartype`, and function-handle grouping or data-variable selectors. Several bin schemes on one variable. Calendar widths (`year`, `week`, `month`, …), duration widths, and datetime edges — the same `EvalError` #1053 already raises. Tall arrays and code generation.

## Test probe that had to move

`tests/unit/test_groupsummary_empty.py::test_unsupported_groupsummary_inputs_are_matlab_errors` listed

```
groupcounts(table([1;1;2],[4;5;6]), 'Var1', 'IncludeEmptyGroups', true)
```

as an error. #1055 makes that call succeed. `Var1` is plain numeric, so the flag adds no rows: counts `[2; 1]`, percents `[200/3; 100/3]`. That result is `test_groupcounts_include_empty_matches_the_published_table`. No previous success-path expected value changed.
