# #1040: detectImportOptions and setvaropts for delimited text

Parent residual of #721. Spreadsheet files stay #1049. This slice does not add `Format` (#1042), `DatetimeType` (#1043), `VariableNamingRule` (#1044), `VariableDescriptions` (#1045), duration/categorical/logical columns (#1046), or the writetable options (#1047, #1048). `Range` landed later in #1041 ([ISSUE-1041-readtable-range.md](ISSUE-1041-readtable-range.md)); the rejection described below is the #1040 slice only.

## What landed

`detectImportOptions(file)` reads a delimited text file and returns a `DelimitedTextImportOptions` value. `setvaropts` copies that value and sets per-variable options. `readtable(file, opts)` imports with the object. `readtable(file, opts, 'ReadVariableNames', false)` is the one extra name-value `readtable` accepts beside an options object; it keeps `opts.VariableNames` and treats the names line as data.

Detection uses the same rule as `readtable`: a column is double when every non-blank, non-placeholder field is numeric, datetime when those fields share one supported date format, and otherwise text (`char`, or `string` with `'TextType','string'`). A column that is only blanks or placeholders is double. Because of that, `readtable(file, detectImportOptions(file))` matches `readtable(file)` for the same name-value arguments both functions accept (`Delimiter`, `ReadVariableNames`, `NumHeaderLines` / `HeaderLines`, `TextType`, `TreatAsMissing`). Blank lines are skipped, including a blank line before the header. `.csv` stays comma-separated unless `'Delimiter'` says otherwise. `.xls`, `.xlsx`, `.xlsm`, `.xlsb`, and `.ods` still raise before any bytes are parsed.

`TreatAsMissing` on `detectImportOptions` is stored on every variable and is excluded from typing, same as the `readtable` name-value. The match stays exact and case-sensitive after stripping.

## Properties this slice reads and writes

| Property | Effect on `readtable(file, opts)` |
|---|---|
| `Delimiter` | One character, or a name such as `'comma'`, `'tab'`, `'semi'`, `'bar'`, `'space'` |
| `VariableNames` | Table variable names. One valid identifier per detected column |
| `VariableTypes` | `double`, `char`, `string`, or `datetime`. `char` imports as a cell array of character vectors |
| `SelectedVariableNames` | Subset and order of columns to import |
| `VariableNamesLine` | `0` means the file has no names line and data starts at line 1. A positive line is the header; data starts on the next physical line |

`setvaropts(opts, Name, Value)` updates every variable. `setvaropts(opts, selection, Name, Value)` updates variables chosen by name, by 1-based index, or by a logical mask. The names it accepts are `Type` and `TreatAsMissing`. A forced `double` or `datetime` stores NaN or NaT when a field does not convert. Text keeps the original field unless the stripped field is a placeholder, which becomes `''` or `<missing>`.

The two classes are ordinary Python objects, not a closed property bag. A later issue adds a field on `VariableImportOptions` (per column) or `DelimitedTextImportOptions` (per file) and teaches `setvaropts` or `readtable` to read it.

## Rejected on purpose

`setvaropts` names other than `Type` and `TreatAsMissing` raise `MATLAB:setvaropts:UnknownParameter`. That includes `FillValue`, `QuoteRule`, and `InputFormat`. Types other than the four above raise `MATLAB:setvaropts:InvalidType` (duration, categorical, and logical are #1046).

`detectImportOptions` and `readtable(file, opts)` reject `'Format'`, `'DatetimeType'`, and `'VariableNamingRule'` as unknown parameters. `'Range'` was rejected in this slice and is accepted by #1041. `'FileType','spreadsheet'` and a spreadsheet extension raise `UnsupportedFileType`. A row that is wider than the options object raises `MATLAB:readtable:ExtraColumns` instead of inventing variables (`ExtraColumnsRule` is not implemented). An empty file raises `MATLAB:detectImportOptions:NoData`.

`getvaropts`, `setvartype`, and `delimitedTextImportOptions` (the constructor that does not read a file) are not this issue.
