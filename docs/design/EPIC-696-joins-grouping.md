# Epic #696 (T-E6): joins and grouping

Milestone: [M10 Tables and data types](../milestones/M10-tables.md), criteria T06 and T07.

## Design (`libs/table_join_group.py`)

- **Keys.** By default the keys are the variables the two tables share. `'Keys'` or `'LeftKeys'`+`'RightKeys'` select them explicitly, and giving both forms is an error. Rows match on typed per-row keys (`table_utils._row_keys`), so numeric, text (cellstr/string/char), categorical, datetime and duration keys compare by value. Key variables of different kinds are a MATLAB error.
- **innerjoin** returns every matching pair (many-to-many gives a cartesian product), sorted by key. The output has the left variables, then the right non-key variables, with `[C, ia, ib]` as outputs.
- **outerjoin** supports `'Type'` full/left/right. Unmatched rows are filled with each type's missing value (`take_filled` appends one missing row and indexes it): NaN, 0 for integers, false, `''`, `<missing>`, `<undefined>`, NaT. Without `'MergeKeys'` both key copies are kept and duplicate names get `_A`/`_B` suffixes from the argument names (MATLAB), or `_left`/`_right` when there is no name. With `'MergeKeys',true` one key column is filled from whichever side is present. Output is sorted by key, computed over the ranks of `[leftKeys; rightKeys]`. `ia`/`ib` are 0 for the missing side.
- **join** keeps the left table's rows and order. It requires unique right keys and a match for every left key, otherwise it raises MATLAB's errors.
- **findgroups** numbers the sorted unique combinations of one or more grouping variables, or a table's variables. Missing values get NaN. The `ID` outputs hold the group values, and a row-vector input gives row outputs.
- **splitapply** applies the function to each group's rows of the data arguments (a table contributes its variables as separate arguments) and stacks the outputs vertically. It supports multiple outputs. MATLAB's checks are enforced: every group number 1..max must occur, outputs must be one row per group, and the size must match.
- **groupsummary(T, groupvars, methods, datavars)** returns the group variables, `GroupCount`, then `<method>_<var>` (variable-major order). Methods are mean/sum/min/max/median/mode/var/std/range/nnz/numunique/nummissing/`'all'`, or function handles (`fun1_<var>`). Missing values are omitted inside groups, and a missing group is its own group, sorted last, unless `'IncludeMissingGroups',false`. **groupcounts** adds `Percent`.

## Adversarial review

- **Probe sweep** (`tests/unit/test_table_join_group.py::test_errors_are_matlab_errors`, 19 cases): unmatched left keys and duplicate right keys in `join`, incompatible key types, no common keys, a non-table input, a bad Type, conflicting key options, LeftKeys without RightKeys, findgroups height mismatch, splitapply with missing group numbers, non-row output, a non-handle, group number 0 and size mismatch, a bad groupsummary method, non-numeric data for a numeric method, a non-table groupsummary input, IncludeEmptyGroups, and an unknown grouping variable. All raise MATLAB errors with no traceback.
- **Type fill** is covered per type: int8 → 0, logical → false, categorical → `<undefined>`, datetime → NaT, string → `<missing>`, cellstr → `''`.
- An unrelated core bug found while probing is filed as #743 (char matrix + string gives an internal error).
- **Name clash:** `join` is also the string function. The table version is used only when the first input is a table. The first full-suite run caught this (`test_string_arrays` join cases) and it was fixed before the PR.
- **No existing test was changed.**
- **Deferred (residual #742):** join KeepOneCopy/row-name keys, cross-type key matching, IncludeEmptyGroups, group bins, groupsummary on arrays, grouptransform/groupfilter.
