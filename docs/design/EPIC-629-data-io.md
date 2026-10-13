# EPIC-629: JSON and delimited numeric I/O (M3-E5)

Criterion **T05** (`m3_t05_data_io`) in [M3](../milestones/M3-domain-toolboxes.md). JSON lives in core `openmatlab/libs/jsonio.py`; `dlmwrite` is extended in `openmatlab/libs/file_builtins.py`. `csvread`/`dlmread` row/column offsets already existed and are covered by the T05 script unchanged.

## jsonencode
- Numeric/logical scalars → number/boolean; integral doubles print without a decimal point, others use shortest round-trip (`pi` → `3.141592653589793`).
- Vectors (row or column) → flat array; matrices and N-D arrays → row-major nested arrays (`a(i,j,k)` is `[i][j][k]`); empty → `[]`.
- NaN/Inf → `null`; with `'ConvertInfAndNaN', false` → `NaN`/`Infinity`/`-Infinity`.
- char row / string scalar → JSON string (standard escaping); char matrix and string arrays → arrays of strings; missing string → `null`.
- Scalar struct → object (field order kept); struct array → array of objects; cell → array (column-major).
- `'PrettyPrint', true` indents by two spaces. Function handles, objects and complex values raise.

## jsondecode
- `null` → `[]`; numbers → double; booleans → logical; strings → char.
- Rectangular arrays of numbers (with `null` → NaN) or booleans → column vector / matrix / N-D array. Arrays of objects with identical (valid-name) keys → Nx1 struct array. Anything else → Nx1 cell.
- Keys pass through makeValidName rules (invalid characters → `_`, leading non-letter gets `x`, keywords get `x` + capitalised); duplicates get `_1`, `_2` suffixes.
- Malformed text raises `MATLAB:json:SyntaxError`.

## dlmwrite
- `'-append'` anywhere in the argument list, positional `delimiter, R, C` offsets, `'roffset'`/`'coffset'`, `'newline'` (`'pc'` → CRLF), plus the existing `'delimiter'` and `'precision'` (digits or format).

## Adversarial review
- `[[1,2]]`-style nesting is easy to collapse wrongly; the unit test pins `[[[1,2]],[[3,4]]]` to a 2x1x2 array.
- A JSON array mixing numbers and `null` stays numeric (NaN), but an all-`null` array is heterogeneous and becomes a cell — matching MATLAB's rule that null only consolidates inside numeric arrays.
- Append mode writes with `newline=''` so CRLF is not doubled on any platform.

## Tests
- `tests/unit/test_json_dlm_io.py`
- `features/json_dlm_io.feature`
- conformance `m3_t05_data_io`

## Residuals
https://github.com/superche/openmatlab/issues/665
