# Epic #691 (T-E1): table core

Milestone: [M10 Tables and data types](../milestones/M10-tables.md), criteria T01 and T02.

## Decision (approved)

`table` keeps its data in its **own column store**, with no pandas. `TableValue` (`runtime/table_value.py`) holds the variable names, the variables and the height. Each variable is an ordinary MATLAB `Value` (numeric or logical matrix, cell, string, char matrix, datetime, …) whose first dimension is the table height. It also holds optional row names and a description. The table is a value type: assignment builds a new `TableValue`.

## Design

- **Row operations go through the evaluator.** Selecting, assigning or growing rows of a variable builds a tiny AST (`v(idx, :)`, `v(idx, :) = x`) over temporary workspace names (`table_subs.ix` / `ix_asgn`). Every value type therefore keeps its own MATLAB indexing and growth rules; the table never re-implements them (KISS, LSP). A bare colon is passed as `None` and becomes a real `ColonExpr`.
- **Indexing hook.** `TableValue.native_subs = True`. `classdef_subs.try_ref` / `try_asgn` (the M8 subsref/subsasgn seam) hand the whole chain to `table_subs.ref` / `asgn` as substruct levels: `T.x(i)`, `T{r,c}`, `T(r,c)`, `T.Properties.VariableNames{k}`, and assignment to each of these. `end` is resolved per level against the value indexed at that level (`T.c(end)` uses the variable's length; `T{end,'a'}` uses the table height). The same hook covers tables nested in struct/cell chains (`s.t.x(2) = v`, through `struct_eval._assign`).
- **Semantics.**
  - `T(r,c)` returns a subtable; `T{r,c}` returns the horizontal concatenation of the selected variables.
  - Variables can be selected by name, cellstr, number, logical mask or `:`. Rows can be selected by number, logical mask, row name or `:`.
  - `T.x = []` deletes a variable. `T(r,:) = []` and `T(:,v) = []` delete rows and variables.
  - `T(r,:) = {…}` assigns contents per variable and can grow the table (cell variables are padded first). A scalar expands when assigned to a whole variable.
  - `[T1;T2]` matches variables by name; `[T1 T2]` needs equal heights and unique names.
  - Errors use MATLAB's wording and identifiers.
- **Construction.**
  - `table(...)` names variables after the caller's argument variables (the same `_call_arg_exprs` seam that `inputname` uses), falling back to `VarN`. It accepts `'VariableNames'` and `'RowNames'`.
  - `array2table`, `cell2table` and `struct2table` follow the MATLAB column rules: uniform numeric scalars become a double column, otherwise the column is a cell.
  - `height`/`width` work on any array; `istable` is added; `isempty`, `size`, `numel`, `class` and `isa` see the table's shape and class.
- **Display.** `  m×n table`, then the header, the underscores, and right-aligned numbers or left-aligned text (`{'x'}`, `"s"`, `true`, datetime text). Row names form a leading column. `disp(T)` omits the size line.

## Adversarial review

- **No recursion through subsref:** tables never go through user `subsref`, and every intermediate value uses the evaluator's default indexing.
- **Temporary names:** they are cleared in `finally`, so nothing leaks into `who`.
- **Height invariants:** checked on construction, dot assignment and row growth; partial-row growth is rejected with a MATLAB error.
- **Probe sweep:** errors (unknown variable, out-of-range row, linear indexing, height mismatch, duplicate or reserved names, operators on tables, bad deletion) are all MATLAB errors with no traceback; see `tests/unit/test_table_core.py`.
- **Deferred (residual #709):** `'Size'`/`'VariableTypes'` preallocation, nested tables, full display fidelity, `uminus` naming, the Workspace Value column.
- **No existing test was changed.**
