# Join options, row-name keys, and expression suffixes (#1052, #1056)

Milestone: M18 Analysis stack deepen (epic #1063). Residuals of epic #696, moved off #742.

## Problem

`join`, `innerjoin`, and `outerjoin` already matched shared variables, explicit `'Keys'` / `'LeftKeys'+'RightKeys'`, and `'MergeKeys'`. Four calls still failed or were wrong:

- `'KeepOneCopy'` was read as another table, so the call said the first two inputs must be tables.
- `'KeepKeys'` was accepted on `join` and ignored. The right key stayed out of the result.
- `'Keys','RowNames'` looked up a variable of that name.
- A cellstr key and a string key matched in `join` (no sort) and failed in `innerjoin` / `outerjoin`, because sorting concatenates the key columns and then rejects the mixed cell. Double and integer keys already matched.

Duplicate non-key names were already suffixed with the argument's variable name, or `_left` / `_right` when `inputname` is empty. `join(T, T)` still died on the duplicate name `x_T`.

## What the public docs say

Clean-room only: MathWorks `join` / `innerjoin` / `outerjoin` / `inputname` pages, and the public Octave table note that records MATLAB's suffix. No product source.

**KeepOneCopy.** Documented on `join` since R2015b: for each named non-key variable, keep the left copy and drop the right one, with no suffix. The current `innerjoin` and `outerjoin` pages do not list the option. #1052 names it for the join family and reserves the "(on join)" qualifier for `KeepKeys`, so this slice accepts it on all three with the same rule.

**KeepKeys.** Not listed on the current `join`, `innerjoin`, or `outerjoin` pages, nor on the R2015b or R2017b public help mirrors, nor in the coder limitations for `join`. The name was already in this function's allowed list and the value was discarded. The only reading that fits `join`'s documented default (right key columns are omitted) is: `true` puts those columns back into the default right-variable list. `false` or omitting the option keeps that default. An explicit `'RightVariables'` replaces the default; `'KeepOneCopy'` still applies after that. `innerjoin` and `outerjoin` do not accept the name.

**Row names.** `'Keys','RowNames'` is the documented backward-compatible form; `'Row'` is the dimension name. The same tokens work in `'LeftKeys'` and `'RightKeys'`. Both tables need row names when `'Keys'` selects them. `join` keeps the left table's row names and row order. `innerjoin` and `outerjoin` attach row names only when row names are a key: the left name when that row is present, otherwise the right name. `'MergeKeys'` merges variable/variable pairs only. A row-name key does not become a data column.

**Cross-type keys.** Cellstr, string, and char are one text kind; double, single, and the integer classes are one numeric kind. A numeric key against a cellstr key stays a type-mismatch error. Same-kind keys compare by value. Sorting must not reject a text pair whose storage differs.

**Suffixes (#1056).** `inputname` is `''` for an expression, an indexing expression, or a call. The `join` examples suffix with the argument's variable name (`Var1_A` beside `Var1_B`). An unnamed input uses `left` or `right`. When both suffixes are the same string, as in `join(T, T)`, the left one gains `_1` (`x_T_1` beside `x_T`). That is the public Octave note that left names are numbered as in MATLAB. It is not `matlab.lang.makeUniqueStrings`, which would number the second name. There is no MathWorks transcript of `join(T, T)` in the pages above; the tests lock this rule. `dataset` `join` (not this function) always uses `_left` / `_right`.

## Design

`libs/table_join_group.py` still owns the three functions.

`'KeepOneCopy'` names must exist on both tables. Those names are removed from the right-hand variable list before suffixing, so the left name stays bare. A name that is only a key is checked and does not add a column.

`'KeepKeys',true` on `join` makes the default right list every right variable. The existing logical flag parser rejects anything other than scalar 0 or 1.

`'Row'` and `'RowNames'` are a sentinel in the key lists, not a variable index. Matching builds a cellstr column from the row names, so the existing text key tuples apply. `join` still stores `A.rownames`. `innerjoin` and `outerjoin` build row names only when a key is that sentinel.

`_row_key_kind` is unchanged, so numeric versus cellstr still errors. Before `innerjoin` / `outerjoin` concatenate keys for the sort, a text pair with different storage (cellstr versus string) is converted to string. Same-storage keys are not converted, so the existing order oracles stay. Numeric mixtures already concatenate. An unmatched `'MergeKeys'` text value is written into the left key's storage (a cellstr key stays a cell, a string key stays a string).

`_caller_arg_names` already returns `''` for a non-name, which the suffix helper maps to `left` / `right`. The new case is identical suffixes: the left suffix becomes `_<name>_1`.

## Non-goals

`groupcounts` on arrays, `grouptransform`, `groupfilter` (#1055). `findgroups` missing-group options and `splitapply` of a table (#1054). `xlsx` (#1049). Calendar `groupsummary` bins. This slice does not change the error-probe list in `test_errors_are_matlab_errors` and does not change any previous success-path expected value.
