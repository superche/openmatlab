# #1045: readtable stores rewritten headers in VariableDescriptions

[`readtable`](https://www.mathworks.com/help/matlab/ref/readtable.html) rewrites a delimited-text header that is not a valid MATLAB identifier. The warning `MATLAB:table:ModifiedAndSavedVarnames` says the original column headers are saved in `VariableDescriptions`. They were not. This slice stores them.

The public table property is a cell array of character vectors, default `{}`. When it is not empty it has one element per variable, and one element may be an empty character vector ([`table` Properties](https://www.mathworks.com/help/matlab/ref/table.html)). The housing walk-through shows the shape this slice uses: before standardizing names, `readtable` saves every original column header, including headers that were already valid identifiers, as a 1-by-N cell ([Data Cleaning and Calculations in Tables](https://www.mathworks.com/help/matlab/matlab_prog/computations-with-numeric-data-in-table-or-timetable.html)).

## When the cell is filled

The cell is filled only when the existing modify / blank-header step changes a name, which is the same step that emits the warning.

| What happened | `VariableDescriptions` |
|---|---|
| `'modify'` (the default) rewrites at least one header | 1-by-N cell of the file's header text for every imported variable. A header that did not change is still stored. The text is the field from the file, not the name after `makeValidName` |
| `'preserve'` of a non-blank header | `{}`. The header is not rewritten, and the warning does not fire |
| A repeated valid identifier, with only the `_1` suffix | `{}`. The suffix is uniqueness, not the rewrite that the warning describes |
| A blank header (`''`), including under `'preserve'` | The warning fires, because the name becomes `VarN`. That field is stored as `''` |
| A whitespace-only header under `'modify'` | Same as a blank header: `makeValidName` reduces it to empty, so it becomes `VarN`. The cell keeps the original spaces |
| A whitespace-only header under `'preserve'` | `{}`. The spaces are a nonempty name, so nothing is rewritten |
| `'ReadVariableNames',false` or an explicit `'VariableNames'` list | `{}`. Those names are not taken from a rewritten header |
| `'Format'` skips the only rewritten column | `{}`. The imported names were not rewritten |

`'VariableNamingRule','preserve'` is unchanged: a non-blank header stays as written, spaces and leading digits included. A spreadsheet extension and `'FileType','spreadsheet'` still raise `UnsupportedFileType` before the file is opened.

## `readtable(file, opts)`

`detectImportOptions` already emits the warning when it rewrites headers. `readtable(file, opts)` does not emit it again. The options object keeps the original header text internally (it is not a public property) and the table built from those options receives the matching cells. `SelectedVariableNames` keeps the originals of the variables that are imported. Changing `VariableNamingRule` on the object still does not rewrite `VariableNames`.

## What else moves with the variables

Indexing, `removevars`, `movevars`, `addvars`, deleting a variable with `T.name = []`, and horizontal concatenation keep one description per remaining variable. A new variable's description is `''`. A table that had `{}` stays `{}`. Vertical concatenation keeps the first table's descriptions. Joins and grouping build a new table and do not copy them. Assigning `Properties.VariableDescriptions` is unchanged: the assignment is not applied.
