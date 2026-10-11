# Feature `done` criteria — Epic #5 (#63) / Issue #67

Per PROCESS § Feature status criteria. Non-goals do **not** block `done`.

## lang.char_literal → done
- Observable: `'hi'`, `''`, `'a''b'`; after value → transpose (`A'`, `[1 2]'`); `.'` CTC
- Tests: `tests/unit/test_char_literal.py`, `tests/bdd/test_char_literal_bdd.py`
- Non-goals: `string` class, char arithmetic

## runtime.char_value → done
- Observable: CharValue for both `'` and `"`; display text
- Tests: char literal unit tests

## lang.cell_literal → done
- Observable: `{a,b;c,d}`, `{}`, mixed Array/Char/nested CellValue; ragged → ParseError
- Tests: `tests/unit/test_cell_literal.py`

## runtime.cell_value → done
- Observable: CellValue shape/numel/get; ConsoleDisplay `{mxn cell}`
- Tests: cell literal unit tests

## lang.cell_index → done
- Observable: `c{i}`, `c{i,j}` content read; `cell(m,n)`; OOB EvalError
- Tests: `tests/unit/test_cell_index.py`
- Non-goals: `c(i)` slice, assignment, cellfun, CSL
