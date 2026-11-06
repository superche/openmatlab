# #1047: writetable and writecell QuoteStrings

Delimited-text [`writetable`](https://www.mathworks.com/help/matlab/ref/writetable.html) and [`writecell`](https://www.mathworks.com/help/matlab/ref/writecell.html) take `QuoteStrings` as `"minimal"` (default), `"all"`, or `"none"`. Both pages were read on 2026-11-06. They do not list `true` or `false`.

Issue #1047 says MATLAB's true/false choice is not implemented. That sentence does not match these pages. This slice follows the pages. `true`, `false`, `'true'`, and `'false'` are `MATLAB:writetable:InvalidQuoteStrings` or `MATLAB:writecell:InvalidQuoteStrings`. The pages do not publish that identifier. The message names the three documented words. Comparison ignores case, as `Delimiter` already does. The example on the writetable page passes `'all'`.

## What each value writes

The writetable example `QuoteStrings','all'` is the oracle for text, numbers, and logicals:

```
Var1,Var2,Var3,Var4
"M",45,"New York, NY",1
"F",41,"San Diego, CA",0
"M",36,"Boston, MA",0
```

`Var1` there is a char column. `table` used to call `.text` while scanning for a name, so that column never reached `writetable`. A char matrix with a row count other than 1 is data, not a parameter name. Each of its rows is one field.

| Value | Fields that are enclosed in `"` |
|---|---|
| `'minimal'` | Any field whose text contains the delimiter, `"` , or a line ending (`\n` or `\r`). This is the default, and it is what omitting the name already did for text |
| `'all'` | Every text, categorical, datetime, and duration value, whether or not it contains those characters. Numbers and logicals stay bare (`1` / `0`) |
| `'none'` | Nothing. A comma inside text is written as a comma |

`writecell` uses the same three words. The writecell page says "variables"; the value in the cell is what is enclosed. A char or string element is text. A datetime, duration, or categorical element follows that class. A number or logical does not.

When a field is enclosed, an embedded `"` is written as `""`. The pages say "enclose in double-quote characters" and do not describe that escape. It is the rule this writer already used, and it is what `readtable` reads back. `'none'` does not enclose, so it does not double quotes either.

The header line is not enclosed. The `'all'` example leaves `Var1,Var2,Var3,Var4` bare, including when a variable name itself contains a comma. Row names are character data in the first column, so they follow the text rule. The pages say "variables" and the example has no row names; this is the reading that makes `'none'` add no quotes and `'all'` quote plain row names such as `r1`.

`NaN`, `NaT`, `<missing>`, and `<undefined>` stay empty fields and are not quoted. That is the algorithms note on the writetable page. A duration whose display text is `NaN` is still those characters, so `'all'` encloses them. A `<missing>` string in a cell is an empty field too, the same as a string column. It used to be written as the characters `None`.

`'minimal'` now also encloses datetime text that contains the delimiter. A space-delimited `02-Jan-2020 03:04:05` is quoted. Datetime text was previously copied through with no quotes.

## What this slice does not change

A spreadsheet extension (`.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.ods`) still raises `UnsupportedFileType` before the file is written. That check runs before the `QuoteStrings` value is judged, so `'QuoteStrings','nope'` on `a.xlsx` is still `UnsupportedFileType` and creates no file. `'FileType','spreadsheet'` on a `.csv` name is still accepted and ignored (#1049). `'WriteMode','append'` is still `MATLAB:textio:textio:UnknownParameter` and creates no file (#1048). `TreatAsMissing` is untouched.
