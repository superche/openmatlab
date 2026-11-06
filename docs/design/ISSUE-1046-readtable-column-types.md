# #1046: readtable duration, categorical, logical, and more dates

Delimited-text [`readtable`](https://www.mathworks.com/help/matlab/ref/readtable.html) and [`detectImportOptions`](https://www.mathworks.com/help/matlab/ref/detectimportoptions.html) still typed a column as double, datetime, or text, and the only date forms were `yyyy-MM-dd[ HH:mm:ss]` and `dd-MMM-yyyy[ HH:mm:ss]`. This slice adds the duration text those pages import, the date forms the public examples already treat as datetime, and the [`setvaropts`](https://www.mathworks.com/help/matlab/ref/matlab.io.text.delimitedtextimportoptions.setvaropts.html) types `duration`, `categorical`, and `logical`.

## What detection records

`detectImportOptions` records the same type `readtable` would use. A column is judged from fields that are not blank and not a `TreatAsMissing` token.

| Column text | Recorded type |
|---|---|
| Every field numeric | `double`, as before |
| Every field one date form below | `datetime`, or `char` / `string` when `DatetimeType` is `'text'` |
| Every field is duration timer text (`hh:mm:ss` or `dd:hh:mm:ss`) | `duration`, or `char` / `string` when `DurationType` is `'text'` |
| Anything else, including `true` / `false` and repeated labels | `char`, or `string` with `'TextType','string'` |

The [setvaropts](https://www.mathworks.com/help/matlab/ref/matlab.io.text.delimitedtextimportoptions.setvaropts.html) preview of `DataWithEmptyFields.csv` shows this split. `00:00:01` is already a duration (an empty field is `NaN`). `TRUE` / `FALSE` is still a cell array of character vectors, and the `Categorical` column is still text, until `setvartype` changes them. [`outages.csv`](https://www.mathworks.com/help/matlab/matlab_prog/create-a-table.html) is the same for labels: `Region` and `Cause` stay text (`string` when `TextType` is `"string"`). `getvaropts` on those names returns text options, and the example then calls `setvartype(..., 'categorical')`.

A column of only blanks or only placeholders stays double. That rule is unchanged.

## Dates

[`readtable`](https://www.mathworks.com/help/matlab/ref/readtable.html) on `outages.csv` imports `2002-02-01 12:18` as datetime ([Create Tables and Assign Data to Them](https://www.mathworks.com/help/matlab/matlab_prog/create-a-table.html)). The same page's file excerpt has no seconds. The setvaropts empty-field preview shows `02/23/2018` as a datetime and `01/14/0018`-style month/day text in that column. `yyyy/MM/dd` is already a form the datetime parser in this repository accepts without an `InputFormat`.

A column is datetime only when every present field is the same form.

| Form | Example |
|---|---|
| `yyyy-MM-dd` | `2020-01-02`, also `2020-1-2` |
| `yyyy-MM-dd HH:mm:ss` | `2020-01-02 03:04:05` or with `T` |
| `yyyy-MM-dd HH:mm` | `2002-02-01 12:18` |
| `dd-MMM-yyyy` | `01-Jan-2020`, also `1-Jan-2020` |
| `dd-MMM-yyyy HH:mm:ss` | `01-Jan-2020 03:04:05` |
| `dd-MMM-yyyy HH:mm` | `01-Jan-2020 12:18` |
| `yyyy/MM/dd` with optional `HH:mm` or `HH:mm:ss` | `2020/01/02` |
| `MM/dd/yyyy` or `dd/MM/yyyy`, same optional clock | `01/14/2018`, `15/03/2021` |

Month and day numbers may be one digit. Minutes and seconds are two digits. There is still no two-digit year: this slice does not invent a pivot year. `MM/dd/uu` stays an explicit `%{fmt}D` format.

Slash order is one choice for the whole column. A field that cannot be a month in the first number (`15/03/2021`) is day-first. A field that cannot be a month in the second number (`01/14/2018`) is month-first. If the column contains both kinds, it is text. If every field can be read either way (`01/02/2021`, `03/04/2021`), the column is month-first. This repository has no `DateLocale` yet, and the public empty-field preview displays that column as month/day. One field on its own, including `readcell`, uses that same month-first default when both readings work.

`'Format','auto'` uses these date forms. The [`readtable`](https://www.mathworks.com/help/matlab/ref/readtable.html) page says `'auto'` produces double, a cell array of character vectors, or datetime. It does not produce duration. A blank or a quoted field still forces text, as #1042 described.

## Duration

[`duration`](https://www.mathworks.com/help/matlab/ref/duration.html) `duration(TimeStrings)` accepts `hh:mm:ss` or `dd:hh:mm:ss`, an optional fractional second, and a leading minus. A leading `+` is not accepted. `6:34:12` and `1:00:54:21` are both legal in one array; the default display format is `hh:mm:ss`, which folds days into hours (`1:00:54:21` displays as `24:54:21`). A column is duration when every present field is one of those two shapes. Parts are elapsed counts, not a clock, so the hour field may be `30`.

`hh:mm` and `mm:ss` are not detected. The duration page requires `InputFormat` for those, and a two-part field does not say which one it is. They stay text until `%{hh:mm}T` or `%{mm:ss}T`.

`DurationType` is the name-value next to `DatetimeType` on `readtable` and `detectImportOptions`.

| Value | Result |
|---|---|
| `'duration'` | Default. A detected duration column is a `duration` array. Empty and placeholder fields are `NaN` |
| `'text'` | That column is text, `char` or `string` following `TextType`. The characters are the field text |

Anything else raises `MATLAB:readtable:InvalidDurationType`. The public pages do not publish that identifier. The message states the documented pair, in the same style as `InvalidDatetimeType`. It is an `EvalError`.

There is no `DurationType` property. `detectImportOptions(..., 'DurationType', ...)` applies the choice while it records `VariableTypes`. `readtable(file, opts)` then imports those types. `readtable(file, opts, 'DurationType', ...)` stays `MATLAB:textio:textio:UnknownParameter`. `setvaropts` does not document `DurationType`; passing it stays `MATLAB:setvaropts:UnknownParameter`.

## Categorical and logical

The [setvaropts `Type` table](https://www.mathworks.com/help/matlab/ref/matlab.io.text.delimitedtextimportoptions.setvaropts.html) lists `'logical'` (for example `true`, `false`, `1`, or `0`), `'duration'`, and `'categorical'`. [`textscan`](https://www.mathworks.com/help/matlab/ref/textscan.html) reads `%C` as a category name and `%T` / `%{fmt}T` as a duration. `%{fmt}T` uses a duration `InputFormat`: `dd:hh:mm:ss`, `hh:mm:ss`, `mm:ss`, `hh:mm`, and a fractional `.S` through `.SSSSSSSSS` on the first three. Text that does not match is `NaN`, which is what textscan documents for `%{fmt}T`.

`setvaropts(..., 'Type', ...)` and `VariableTypes` accept `duration`, `categorical`, and `logical` in addition to the four types from #1040. A type outside that list, such as `'single'`, is still `MATLAB:setvaropts:InvalidType`.

| Forced type | Field text |
|---|---|
| `duration` | The same timer text as detection. `hh:mm` without a format is `NaN`. A placeholder or a blank is `NaN` |
| `categorical` | A category name. Names are sorted, the order `categorical` already uses. A blank, a placeholder, or the characters `<undefined>` is `<undefined>` and is not a category |
| `logical` | `true` and `t` are true. The match is case-insensitive, so `TRUE` is true |

The default logical symbols are the ones `getvaropts` prints on the public answers page [readtable not reading logical values as expected](https://www.mathworks.com/matlabcentral/answers/895897-readtable-not-reading-logical-values-as-expected): `TrueSymbols` `{'true','t'}`, `FalseSymbols` `{'false','f'}`, `CaseSensitive` `0`, `FillValue` `0`. MathWorks staff on that page say `1` and `0` are detected as numeric, and that a logical import treats text which is not a true or false symbol as the fill value false (`ImportErrorRule` `'fill'`). This slice does the same. `'1'` forced to logical is false. `setvaropts` still rejects `TrueSymbols`, `FalseSymbols`, and `CaseSensitive` as unknown parameters, so those defaults cannot be replaced yet.

`%C` and `%T` follow the quote rule `%q` already uses. `'Format','auto'` does not apply them. An explicit `%f` on timer text is still a double column of `NaN`.

## `TreatAsMissing`

On double, datetime, and text the tokens are unchanged: `NaN`, `NaT`, `''`, or `<missing>`.

The same tokens are left out of duration detection. On a duration column they are `NaN`, which `ismissing` already reports. On a categorical column they are `<undefined>`, which `ismissing` already reports. On a logical column they become false, the documented fill value. Logical false is not a missing value, and this slice does not add one.

## What still rejects the file

A spreadsheet extension (`.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.ods`) raises `UnsupportedFileType` before the file is opened, including when `DurationType` is not a legal value. `'FileType','spreadsheet'` does the same, and it is checked before the value. `%c` and scansets stay `MATLAB:readtable:InvalidFormat`. A duration format that is not an `InputFormat`, including `hh:mm.SS`, is the same error. Spreadsheet import (#1049), `QuoteStrings` (#1047), and `WriteMode','append'` (#1048) are unchanged.
