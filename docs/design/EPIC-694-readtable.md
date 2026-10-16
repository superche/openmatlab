# Epic #694 (T-E4): readtable / writetable / readcell / writecell

Milestone: [M10 Tables and data types](../milestones/M10-tables.md), criterion T08 (absorbs the `readtable` part of #577).

## Design (`libs/table_io.py`)

- **Splitting.** Python's `csv` module splits fields, so quoted fields with embedded delimiters or quotes work. Blank lines are skipped. The delimiter is `,` for `.csv`. Otherwise it is sniffed among `, \t ; |` (a delimiter that appears the same nonzero number of times on the first lines wins), with whitespace as the fallback. `'Delimiter'` overrides this and accepts MATLAB names such as `'tab'` and `'semi'`.
- **Column typing.** Each column is typed from its non-empty fields. If all are numeric (including `NaN`/`Inf`), the column is double and empty fields become NaN. If all are dates in one format (`yyyy-MM-dd`, `yyyy-MM-dd HH:mm:ss`, `dd-MMM-yyyy`, …), the column is datetime with that `Format` and empty fields become NaT. Otherwise the column is a cellstr, or a string array with `'TextType','string'`.
- **Names.** Header names pass through a `matlab.lang.makeValidName` equivalent: whitespace is removed and the next letter capitalized, invalid characters become `_`, a leading non-letter gets an `x` prefix, and duplicates become `_1`. When a name changes, MATLAB's `MATLAB:table:ModifiedAndSavedVarnames` warning is issued. `'ReadVariableNames',false` gives `Var1…`. `'VariableNames'` and `'NumHeaderLines'` are supported.
- **writetable.** Writes a header row (`'WriteVariableNames'`) and an optional `Row` column (`'WriteRowNames'`). A multi-column variable becomes `name_1, name_2, …`. NaN, NaT, `<missing>` and `<undefined>` are written as empty fields. Text is quoted only when needed, logicals are written as 1/0, and datetimes use their `Format`, so values round-trip through `readtable`.
- **readcell / writecell.** In `readcell`, numbers become doubles, dates become datetime, text becomes char, and empty fields become `missing`. `writecell` writes scalars and text. Nested cells are an error.
- `isnat` is added: readtable produces NaT, and T09 will use it too.
- **Spreadsheet files** (`.xlsx`, …) are a milestone non-goal and raise a clear MATLAB error.

## Adversarial review

- **Probe sweep:** a missing file, a spreadsheet extension, a non-text file name, an unknown parameter, a non-table or non-cell first input, nested cells, a bad `TextType`, and a `VariableNames` count mismatch all raise MATLAB errors with no traceback (`tests/unit/test_table_io.py`).
- **Ragged rows** are padded with empty fields, which become NaN or `''`.
- **No existing test was changed.**
- **Deferred (residual #721):** import options, `VariableDescriptions` for modified headers, `VariableNamingRule`, encodings, more date formats, `QuoteStrings`/append.
