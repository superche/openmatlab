# #1044: readtable VariableNamingRule for delimited text

`VariableNamingRule` is a name-value of [`readtable`](https://www.mathworks.com/help/matlab/ref/readtable.html) and [`detectImportOptions`](https://www.mathworks.com/help/matlab/ref/detectimportoptions.html) for text files, and a property of [`DelimitedTextImportOptions`](https://www.mathworks.com/help/matlab/ref/matlab.io.text.delimitedtextimportoptions.html). The public pages list two values:

| Value | Delimited text |
|---|---|
| `'modify'` | Default. Invalid variable names, as determined by `isvarname`, are converted to valid MATLAB identifiers. This slice keeps the makeValidName path `readtable` already uses ([`matlab.lang.makeValidName`](https://www.mathworks.com/help/matlab/ref/matlab.lang.makevalidname.html): delete whitespace and capitalize the following letter, replace other non-identifier characters, prefix a leading non-letter). Omitting the name is this value |
| `'preserve'` | Keep the header text as the variable name, including spaces, punctuation, leading digits, and other text that is not a valid MATLAB identifier |

The public pages do not publish an identifier for a bad value. Anything that is not one of those two strings raises `MATLAB:readtable:InvalidVariableNamingRule`. The message states the documented constraint. The match is case-insensitive, same as `DatetimeType`. It is an `EvalError`.

A repeated header still gets the `_1`, `_2` suffix the modify path already appends, because table variable names have to be unique. A blank header still becomes `VarN`, because a variable name has to be nonempty. That suffix is applied after the rule, and it is the same step for both values. When the modify / blank-header step changes a name, the original headers are written to `VariableDescriptions` (#1045, [ISSUE-1045-readtable-variabledescriptions.md](ISSUE-1045-readtable-variabledescriptions.md)). The modified-name warning still fires only on that step. `'preserve'` of a non-blank header does not fire it.

## Where the name is accepted

`detectImportOptions(..., 'VariableNamingRule', ...)` applies the choice while it detects `VariableNames`, and stores the same choice on `VariableNamingRule`. `readtable(file, opts)` then imports those names. The public property page says variable names are not refreshed when the value changes from `'modify'` to `'preserve'`. This object does not keep a second copy of the header text, so changing the property in either direction does not rewrite `VariableNames`.

Assigning `VariableNames` follows the current property. Under `'modify'`, a name that is not a valid MATLAB identifier is still `MATLAB:table:InvalidVarNames`. Under `'preserve'`, the public `VariableNames` description allows those names, so the assignment is kept and `readtable(file, opts)` uses it. Names still have to be nonempty and unique.

`readtable(filename, opts, Name=Value)` accepts only `ReadVariableNames`, `ReadRowNames`, `DateLocale`, and `Encoding` for text files. This repository still implements only `ReadVariableNames` of that list. `readtable(file, opts, 'VariableNamingRule', ...)` stays `MATLAB:textio:textio:UnknownParameter`.

An explicit `'VariableNames'` on `readtable` is still the names to use. The rule does not run makeValidName on that list.

`'Format'`, `'Range'`, `'Delimiter'`, `'DatetimeType'`, and `'ReadVariableNames',false` are unchanged apart from which names a header row receives. `ReadVariableNames` false still yields `Var1`, ….

## What still rejects the file

A spreadsheet extension (`.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.ods`) raises `UnsupportedFileType` before the file is opened, including when `VariableNamingRule` is `'preserve'` or not a legal value. `'FileType','spreadsheet'` does the same, and it is checked before the value. Duration, categorical, and logical columns stay #1046.
