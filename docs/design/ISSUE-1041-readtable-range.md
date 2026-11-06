# #1041: readtable Range for delimited text

`Range` selects a window of a delimited text file. Spreadsheet ranges stay #1049. This slice does not add `Format` (#1042), `DatetimeType` (#1043), `VariableNamingRule` (#1044), `DataLines` as a property, or `ExpectedNumVariables`.

Public `readtable` and `detectImportOptions` both take `Range` for text files. `DelimitedTextImportOptions` has no `Range` property. The row part of a text range is `DataLines` on that object, and #1040 left `DataLines` unset on purpose. This slice does not add that property. A range passed to `detectImportOptions` is stored as internal line and column bounds. `readtable(file, opts)` uses those bounds. `readtable(file, opts, 'Range', ...)` is still an unknown parameter: the only name-value beside an options object remains `ReadVariableNames`.

## Forms

Rows and columns are 1-based physical lines and fields. A1 letters are not case sensitive. Opposing corners are ordered, so `C4:B2` is `B2:C4`. An empty `Range` is the same as omitting it (no extra trim).

| Form | Window |
|---|---|
| `'A5'` or `[5 1]` | Start at that cell. Rows run through the last line of the file. Columns run from the start column through the last column that has a non-blank field, so a trailing all-empty column is dropped. |
| `'D2:H4'` or `[2 4 4 8]` | That rectangle, inclusive. Empty fields stay in the window and import as missing. The width is exactly the column span, including columns past the end of a short line. |
| `'1:7'` | Those lines. Columns run from the first non-blank column through the last. |
| `'A:F'` | Those columns, for every non-blank line from the first one to the end of the file. This is the only form that accepts `NumHeaderLines` or `HeaderLines`. |
| `'myTable'` | Error. Named ranges are spreadsheet-only. No workbook is opened. |

The first kept line is the variable-name line when `ReadVariableNames` is true (the default), including for a start cell that is not on row 1. `ReadVariableNames` false keeps that line as data and names the columns `Var1`, `Var2`, …. A blank line (nothing left after stripping) is not a row, same as `readtable` without `Range`. A field that is only spaces is empty for column trimming and for typing.

`NumHeaderLines` with any form other than `'A:F'` raises `MATLAB:textio:textio:InvalidRange` before the file is read. With `'A:F'`, those lines are skipped and the column window then starts at the first remaining non-blank line. A range that starts past the end of the file, or that contains no data, raises the same identifier. A spreadsheet extension still raises `UnsupportedFileType` before any bytes are read, including when `Range` is also passed.

`detectImportOptions(file, 'Range', ...)` detects only inside that window, so the options object has one variable per selected column. `VariableNamesLine` together with `Range` raises `MATLAB:detectImportOptions:InconsistentOptions`. `setvaropts` still copies the hidden bounds, so a later `readtable(file, opts)` stays inside the window. Setting `VariableNamesLine` afterwards moves the name line the way #1040 already does and does not clear the end line or the columns.

`ExpectedNumVariables` is still an unknown parameter, so a rectangle is not checked against a caller-supplied width. Omitting `Range` does not start trimming the used range; a file with a trailing empty field still has that column, and only an explicit start cell or row range drops all-empty columns.
