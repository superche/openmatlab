# groupsummary bins, array input, and naming (issue #1053)

Milestone: M18 Analysis stack deepen (epic #1063). Parent residual of #742 / epic #696.

## Problem

`groupsummary` already aggregated a table and, since #742, filled empty groups for a column-vector grouping variable. The calls still rejected were the ones #1053 lists: binning (including `'IncludedEdge'`), a non-table `groupsummary(X, G, method)` with `[B,BG,BC]`, a function that returns more than one value, `'IncludeEmptyGroups'` on a multi-column grouping variable, and `'VariableNamingRule'`.

## Design

`libs/table_join_group.py` still owns the function. Binning rewrites the grouping columns, then the existing group numbering runs, including the #1060 missing-key ranks and the #742 empty-group product.

**Bins.** A numeric vector of two or more finite, strictly increasing edges, or one positive integer (that many equal-width bins from the finite minimum to the maximum; a single finite value is widened by 0.5 on each side, the same rule as `histcounts` here). The result is an ordinal categorical. Labels follow `discretize`: `'IncludedEdge','left'` (the default) is `[a, b)` and a closed last bin; `'right'` closes the first bin and uses `(a, b]` after that. A value outside the edges is missing. The output name is `disc_<var>`. `'none'` does not bin. One scheme applies to every grouping variable; a cell array supplies one scheme per variable. Several schemes for a single variable (R2024a) stay an error.

`'IncludedEdge'` without a bin argument is an error. Datetime grouping accepts the schemes whose labels the documentation names: `dayname` (Sunday through Saturday), `monthname` (January through December), and the integer `*of*` units (`hourofday` 0–23, `dayofweek` 1–7, and the rest of that table). The name is `<unit>_<var>`. `'IncludeEmptyGroups'` then sees every category, so an unused bin or an unobserved day is a row. Calendar widths (`year`, `week`, …), duration widths, and datetime edges are an `EvalError`, not a traceback.

**Empty groups and width.** A multi-column grouping variable is one key, the whole row. The flag does not cross its columns. A column vector is unchanged: every category, both logical values, or the numeric values that occur. An array matrix is different, because each column is its own grouping vector, and those vectors do combine.

**Array input.** `B` has one row per group. Columns follow the table order: each data column, then each method. `[B,BG,BC]` adds the grouping values and the counts. One grouping vector comes back as itself; several come back as a row cell. A function with more than one input takes a cell of arrays and pairs columns, the same way a table pairs a cell of `datavars`.

**Methods.** A function may return one row, including a row of several columns. A named function with several declared outputs is called with that many outputs and the outputs are placed side by side in the one summary variable. `varargout` stays one output. Named methods still skip NaN; a function does not.

**Names (R2026b).** `'VariableNamingRule'` is `'numbered'` (the default: `mean_x`, `fun1_x`, `fun2_x`), `'methodname'` (the prefix is `func2str`), or `'noprefix'` (the data-variable name, and only when there is one method). It does not rename the grouping columns or `GroupCount`, and it is rejected for array input. The prefix is per method, repeated for each data variable.

## Non-goals

`groupcounts` on arrays, `grouptransform`, `groupfilter` (#1055). `findgroups` missing-group options and `splitapply` of a table (#1054). Join options landed later (`docs/design/EPIC-1052-join-options.md`, #1052, #1056). Calendar bin widths, datetime edges, and more than one bin scheme on one variable.
