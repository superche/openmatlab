# Epic #693 (T-E3): table utilities, sorting and sets

Milestone: [M10 Tables and data types](../milestones/M10-tables.md), criteria T03 and T05 (absorbs the table/string set-ops part of #585, which stays on the Core backlog).

## Design (`libs/table_utils.py`)

- **Evaluator access.** Builtins get the calling evaluator from the `frames` stack. Rows are selected with `TableValue.take_rows` and the existing `table_subs.ix`, and values are concatenated with the new `Evaluator.concat_values(rows)`, which is the body of `[...]` split out of `_eval_matrix` with no behaviour change. So every variable type keeps its own MATLAB indexing and concatenation rules, and the table code never special-cases types.
- **Conversions.** `table2array` is `[T.Var1, T.Var2, …]` (a type mix such as a cell next to a double is a MATLAB error). `table2cell` returns m×n, and a cellstr variable contributes its char contents. `table2struct` gives an m×1 struct array, or with `'ToScalar',true` a scalar struct of columns.
- **head/tail** take k rows (default 8) of a table or of any array.
- **varfun** applies the function to each variable and names the outputs `<fun>_<var>` (anonymous functions use `Fun`). It supports `'InputVariables'` and `'OutputFormat'` table/uniform/cell. **rowfun** passes each row's variables as separate inputs (`'SeparateInputs'`) and stacks the outputs vertically with `concat_values`. It also supports `'OutputVariableNames'` and `'NumOutputs'`.
- **removevars / renamevars / movevars / addvars** support `'Before'`/`'After'` by name or index and `'NewVariableNames'`. `addvars` infers names from the workspace variables passed in, as `table()` does. Name rules (duplicates, reserved names) are enforced by `TableValue.check_names`.
- **summary** prints the classic MATLAB layout. Numeric variables show Min/Median/Max (+NumMissing), logicals show True/False counts, categoricals show per-category counts, and datetime/duration show Min/Median/Max.
- **Ordering.** Each variable becomes float *rank columns*: numeric columns as values, cellstr/string/char as sorted-unique ranks, categorical as category codes, and datetime/duration as values. Missing values (NaN/NaT/`<missing>`/`<undefined>`) are NaN. `sortrows(T, vars, dirs)` performs a stable multi-key sort, putting NaN last when ascending and first when descending (MATLAB's `'auto'`). It accepts names, indices (a negative index means descend), `'RowNames'`, or a single direction, and returns the index as its second output. `issortedrows` compares the keys with the sorted order.
- **Sets on tables.** `unique(T)` returns sorted unique rows with `ia` (first occurrence) and `ic`. `ismember(A,B)` matches rows by typed per-row keys, aligns variables by name, and returns `tf` and `loc`. Categorical gets `sort` (category order, `<undefined>` last, `[B,I]`, direction) and `ismember` against categorical arrays or text.

## Adversarial review

- **Probe sweep** (`tests/unit/test_table_utils.py::test_errors_are_matlab_errors`, 20 cases): incompatible `table2array`, non-table inputs, a negative `k`, non-scalar uniform output, a non-handle function, GroupingVariables, a bad OutputFormat, an unknown variable, a rename count mismatch, a duplicate name after rename, Before+After together, a wrong-height `addvars`, a bad direction, a non-cellstr cell sort key, `'RowNames'` without row names, `unique 'stable'`, table vs non-table, disjoint variable names, and a bad categorical `ismember`/`sort` direction. All raise MATLAB errors with no traceback.
- **NaN placement bug found and fixed:** the first draft put NaN last for `'descend'` as well. MATLAB puts it first.
- **Existing behaviour:** numeric `sort`/`sortrows`/`unique`/`ismember` paths are untouched (the wrappers only intercept table or categorical inputs), and `_eval_matrix` → `concat_values` is a pure extraction. **No existing test was changed.**
- **Deferred (residual #738):** grouped varfun/rowfun, summary struct output and the modern layout, MissingPlacement, `unique 'stable'` and the other set operations on tables, and anonymous-function multi-output in rowfun.
