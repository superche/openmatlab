# M17 slice of #721: readtable TreatAsMissing (CSV)

Milestone: [M17 Analyst pipeline](https://github.com/superche/openmatlab/milestone/17), parent epic #1032. This is the delimited-text slice of #721, not a new epic.

## Problem

An analyst CSV uses tokens such as `NA`, `-999`, and blank fields for missing measurements. `readtable` already turns a blank numeric or datetime field into NaN or NaT. A listed token was ordinary text, so it forced the column to cellstr and `ismissing` / `rmmissing` / `fillmissing` (#1033) never saw it.

## Design

`readtable` accepts `'TreatAsMissing'` as a character vector, a string array, or a cell array of character vectors. Each entry is one placeholder. Leading and trailing whitespace is stripped on the placeholder and on the field. The comparison is exact and case-sensitive: `'NA'` does not match `'N/A'` or `'null'`, and `'1.0'` does not match `'1'`.

A matching field is ignored while the column is typed, then stored as the standard missing value for the type that the other fields select:

- double: NaN
- datetime: NaT
- cellstr (`'TextType','char'`, the default): `''`
- string (`'TextType','string'`): `<missing>`

A blank field is already missing for double and datetime. Listing `''` also makes a blank or whitespace-only text field missing (`''` or `<missing>`). A column whose every field is blank or a placeholder stays double NaN, the same fallback an all-blank column already used.

The name-value is read in `libs/table_io.py` on the delimited-text path (the csv module, so a `.csv` keeps empty fields). `.xls` / `.xlsx` / `.xlsm` / `.xlsb` / `.ods` still raise `MATLAB:readtable:UnsupportedFileType`. Delimited-text `detectImportOptions` / `setvaropts` is a later slice: [`ISSUE-1040-import-options.md`](ISSUE-1040-import-options.md).

A value that is not text, a multi-row char matrix, or a `<missing>` string raises `MATLAB:readtable:InvalidTreatAsMissing`. Name-value options this slice does not implement raise `MATLAB:textio:textio:UnknownParameter`. Both are `EvalError`s. Later issues accepted `'Range'` (#1041), `'Format'` (#1042), and `'DatetimeType'` (#1043). `'VariableNamingRule'` is still unknown.

## #1039

This slice does not depend on #1039 and does not touch `missing_builtins.py`. The placeholders become NaN, NaT, empty char inside a cell, or string `<missing>`, which `ismissing` already reports. The tests use tables of height at least 2 whose variables are column vectors. They do not call `ismissing` on a char array, do not call `ismissing` / `rmmissing` / `fillmissing` on a 0-row table, do not check `rmmissing(A,2)`'s second output, and do not call `fillmissing` on a single-row table.

## Left on the backlog

The delimited-text `detectImportOptions` / `setvaropts` slice has since landed ([`ISSUE-1040-import-options.md`](ISSUE-1040-import-options.md)). The other rows are unchanged.

| Item | Issue |
|---|---|
| `detectImportOptions` / `setvaropts` for delimited text | [#1040](https://github.com/superche/openmatlab/issues/1040), [`ISSUE-1040-import-options.md`](ISSUE-1040-import-options.md) |
| `'Range'` | #1041 |
| `'Format'` | #1042 |
| `'DatetimeType'` | #1043 (delimited text; see [ISSUE-1043-readtable-datetimetype.md](ISSUE-1043-readtable-datetimetype.md)) |
| `'VariableNamingRule','preserve'` | #1044 |
| original headers not saved in `VariableDescriptions` | #1045 |
| duration, categorical, logical, and further date formats | #1046 |
| `writetable` `'QuoteStrings'` (accepted, no effect) | #1047 |
| `writetable` `'WriteMode','append'` | #1048 |
| spreadsheet I/O (explicit non-goal) | #1049 |
| encodings (already tracked, not re-filed) | #577 |
