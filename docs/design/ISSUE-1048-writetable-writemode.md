# #1048: writetable WriteMode for delimited text

Delimited-text [`writetable`](https://www.mathworks.com/help/matlab/ref/writetable.html) takes `WriteMode` as `'overwrite'` (default) or `'append'`. The page was read on 2026-11-06. The text-file row of that argument is the whole of this slice. The page example writes `InsectCollection.txt`, then appends with `'WriteMode','Append'` and `'WriteVariableNames',false`.

| Value | What delimited text does |
|---|---|
| `'overwrite'` | Replace the file. This is the default, and it is what omitting the name already did |
| `'append'` | Add the rows from this call to the end of the file. If the file does not exist, create it and write those rows |

Comparison ignores case, as `Delimiter` and `QuoteStrings` already do. `'Append'` and `"append"` are the same mode.

`'append'` is not supported when `WriteVariableNames` is true. That bullet on the page is not under the spreadsheet-only list, and the text example passes `false`. The default of `WriteVariableNames` is true, so `'WriteMode','append'` with no `WriteVariableNames` is the unsupported combination. It raises `MATLAB:writetable:AppendNotSupported` and does not create or change a file. The page does not publish that identifier. The message names the documented rule.

A new file written with `'append'` and `'WriteVariableNames',false` has data rows only. There is no header, because a header would require `WriteVariableNames` true. An existing file keeps every byte it already had. The new rows use this call's `Delimiter`, `QuoteStrings`, and `WriteRowNames`. They are not applied back to the earlier lines. Row names are data in those rows. The header word for the row-name column is only written when `WriteVariableNames` is true, which cannot combine with `'append'`.

If the existing file is non-empty and its last byte is not LF or CR, one LF is written before the new rows. The page says "append data" for a line-oriented text file, and the example reads the result back as one more table row. A file that already ends on a line boundary does not gain a blank row. An empty table appends nothing and leaves an existing file untouched.

A value other than `'overwrite'` or `'append'` is `MATLAB:writetable:InvalidWriteMode`. The page does not publish that identifier. The message names the two text modes. Spreadsheet modes (`'inplace'`, `'overwritesheet'`, `'replacefile'`) are not text modes, so they use that same error. They do not write a spreadsheet.

## What this slice does not change

A spreadsheet extension (`.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.ods`) still raises `UnsupportedFileType` before any bytes. That check runs before the `WriteMode` value is judged, so `'WriteMode','nope'` on `a.xlsx` is still `UnsupportedFileType` and creates no file. `'FileType','spreadsheet'` on a `.csv` name is still accepted and ignored (#1049). On that name, `WriteMode` is still the text mode: `'append'` appends text, and `'inplace'` is `InvalidWriteMode`.

`writecell` does not take `WriteMode`. The name stays `MATLAB:textio:textio:UnknownParameter`, including on a spreadsheet extension, and no file is created. A second `writecell` of the same path still replaces the file. `QuoteStrings` and `TreatAsMissing` are unchanged. `Range` is not a delimited-text write argument on this page.
