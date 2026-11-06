# #1043: readtable DatetimeType for delimited text

`DatetimeType` is a name-value of [`readtable`](https://www.mathworks.com/help/matlab/ref/readtable.html) and [`detectImportOptions`](https://www.mathworks.com/help/matlab/ref/detectimportoptions.html) for text files. The public pages list three values:

| Value | Delimited text |
|---|---|
| `'datetime'` | Default. A column whose non-blank, non-placeholder fields share one supported date form is a `datetime` array. Empty and placeholder fields are NaT |
| `'text'` | That same column is text. `'TextType','char'` (the text-file default) stores a cell array of character vectors. `'TextType','string'` stores a string array. The characters are the field text, not a reformatted datetime |
| `'exceldatenum'` | Documented as valid only for spreadsheet files. Delimited text raises `MATLAB:readtable:ExcelDateNumText` |

A value that is not one of those three raises `MATLAB:readtable:InvalidDatetimeType`. The public reference pages do not publish those identifiers; the messages state the documented constraint, in the same style as `MATLAB:readtable:InvalidTextType`. Both are `EvalError`s.

Numeric columns, text columns, and a column of only placeholders stay as they are. `'text'` does not parse a numeric column as an Excel serial date. Mixed date forms stay text. `setvaropts(..., 'Type', 'datetime')` can still force a column back to `datetime` after detection.

## Where the name is accepted

`DelimitedTextImportOptions` has no `DatetimeType` property. `detectImportOptions(..., 'DatetimeType', ...)` applies the choice while it detects `VariableTypes`, so `readtable(file, opts)` then imports those types. `'text'` records `char` or `string` on that column. Omitting the name, or passing `'datetime'`, leaves the detected type `datetime`.

`readtable(filename, opts, Name=Value)` accepts only `ReadVariableNames`, `ReadRowNames`, `DateLocale`, and `Encoding` for text files. This repository still implements only `ReadVariableNames` of that list. `readtable(file, opts, 'DatetimeType', ...)` stays `MATLAB:textio:textio:UnknownParameter`, the same rule #1042 used for `Format`.

`setvaropts` does not document `DatetimeType`. Passing it as a variable option stays `MATLAB:setvaropts:UnknownParameter`. Per-column type remains `Type`.

`'Format'` still types columns from its specifiers. `'DatetimeType','text'` then stores a `%D` or `%{fmt}D` column as the field text (after that specifier's width and quote rules) instead of a datetime. Other specifiers are unchanged, so `%s` on a date stays text even when `DatetimeType` is `'datetime'`. `'Format','auto'` detects as before, including its blank and quoted-field rules, and `'text'` applies only to a column that came out `datetime`.

## What still rejects the file

A spreadsheet extension (`.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.ods`) raises `UnsupportedFileType` before the file is opened, including when `DatetimeType` is `'exceldatenum'` or `'text'`. `'FileType','spreadsheet'` does the same. `'VariableNamingRule'` stays an unknown parameter (#1044). Duration, categorical, and logical columns stay #1046. There is still no public `DataLines` or `Range` property.
