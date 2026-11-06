# #1042: readtable Format for delimited text

`Format` is a name-value of `readtable` for a delimited text file. It is either `'auto'` or a character vector / string scalar of [textscan](https://www.mathworks.com/help/matlab/ref/textscan.html) conversion specifiers. The public `readtable` page documents both, and the R2020a version history says omitting `Format` follows `detectImportOptions` while `'Format','auto'` restores the previous typing rules. This slice does not add `DatetimeType` (#1043), `VariableNamingRule` (#1044), duration/categorical/logical columns (#1046), or any spreadsheet reader (#1049).

`DelimitedTextImportOptions` has no `Format` property in the current public property list; column types live on `VariableTypes`. `detectImportOptions(..., 'Format', ...)` and `readtable(file, opts, 'Format', ...)` stay `MATLAB:textio:textio:UnknownParameter`, the same way `readtable(file, opts, 'Range', ...)` stayed unknown in #1041. The only name-value beside an options object is still `ReadVariableNames`.

Omitting `Format` is unchanged.

## Explicit specifiers

One specifier is one delimited column, left to right, after `Range` selects its window. Spaces between specifiers are ignored. `%s %f` and `%s%f` are the same. A comma or any other literal between specifiers is `MATLAB:readtable:InvalidFormat` — the public examples are `%s%s%u%f%f%s` and `%f%f`, not a comma-separated list. Extra file columns are dropped. A short row is padded with empty fields. `%*` skips that column, including `%*u32` and `%*3s`: the width on a skipped specifier does not return the rest of the field as the next variable. The whole delimited field is skipped.

| Specifier | Column |
|---|---|
| `%f` `%f64` `%n` | double. Empty, a `TreatAsMissing` token, or a non-numeric field is NaN |
| `%f32` | single, same missing rule |
| `%d` `%d8` `%d16` `%d32` `%d64` `%u` `%u8` `%u16` `%u32` `%u64` | that integer class. `%d` is int32 and `%u` is uint32, as textscan documents |
| `%x` `%xu8` `%xu16` `%xu32` `%xu64` `%xs8` `%xs16` `%xs32` `%xs64` | hex, optional `0x`. The class is the textscan class (`%x` is uint64) |
| `%b` `%bu8` `%bu16` `%bu32` `%bu64` `%bs8` `%bs16` `%bs32` `%bs64` | binary, optional `0b` |
| `%s` | cellstr, or a string array when `'TextType','string'` |
| `%q` | same as `%s` after the textscan quote rule: a leading `"` and its closing `"` are removed and `""` becomes `"` |
| `%D` | datetime, using the date forms `readtable` already detects. Anything else is NaT |
| `%{fmt}D` | datetime parsed with the same format letters as `datetime` `'InputFormat'`. Text that does not match is NaT, which is what textscan documents, not a parse error |

A field width (`%5f`, `%5s`) keeps that many characters of the field, then converts. `%5f` reads `123.456` as `123.4`. A precision (`%7.2f`) then keeps that many digits after the decimal point, so `%7.2f` reads `123.456` as `123.45`. Precision on a non-float specifier is an error.

Integer conversion uses the same rounding and saturation as the integer classes: half away from zero, NaN becomes 0, values clip to the class range. An empty integer field is therefore 0. There is still no public `FillValue`.

`%c`, scansets (`%[abc]`), `%C`, and `%T` / `%{fmt}T` raise `MATLAB:readtable:InvalidFormat`. `%c` and scansets read across delimiters, which is not a column of a delimited file. Categorical and duration columns are #1046.

`%D` does not grow the set of date forms (#1046). `%{fmt}D` can name a format, but month names are only as reliable as the `datetime` parser already is.

## `'auto'`

From the public page: a column whose fields are all numeric is double; otherwise it is a cell array of character vectors, or a datetime array when the values are dates. `'TextType','string'` still selects a string array instead of a cell array. The R2020a table of previous behavior is applied where it does not invent a second naming rule:

| Input | `'auto'` |
|---|---|
| Blank field, and `''` is not a `TreatAsMissing` token | The column is text. The blank is `''` (or `<missing>` for string), not NaN/NaT |
| Quoted field | Text, even when the characters are numeric or a date. The stored text is the csv-unquoted field |
| `TreatAsMissing` token | Left out of typing, then stored as the usual missing value. A column of only tokens stays double. Listing `''` makes a blank a token, so the column can stay numeric |
| Every non-blank, non-token field is a date in one supported form, and none of those fields is quoted | datetime |
| Lines with different field counts | `MATLAB:readtable:UnequalDelimiters`. A quoted comma is not a delimiter. Blank lines are still skipped |
| `12abc` in one field | Stays one field (text, if the column is not otherwise numeric). The R2020a note says the old reader treated the trailing junk as its own field. Doing that inserts a column between this field and the next, and the header row does not have a name for it |

Names still come from the first kept row, passed through the existing `makeValidName` path. This repository's default `readtable` already does that, including when the first row is numeric (`1` becomes `x1`). `'VariableNamingRule','preserve'` remains #1044. There is no second header-line detector, so `'auto'` and the default agree on a file that is only numbers, dates, and ordinary text.

A file with no non-blank line is `MATLAB:readtable:NoData` for `'auto'`. A header and no data rows matches `readtable` without `Format`: a zero-row table of text columns, because there are no values to call numeric. An explicit format on an empty file is a zero-row table whose columns are the specifiers.

## What still rejects the file

A spreadsheet extension (`.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.ods`) raises `MATLAB:readtable:UnsupportedFileType` before the file is opened, whether or not `Format` is also passed. `'FileType','spreadsheet'` does the same. `'MultipleDelimsAsOne'`, `'DatetimeType'`, and `'VariableNamingRule'` are still unknown parameters.
