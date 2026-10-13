# Design: Epic #535, core arrays and sets (M7 C06)

Covers #553 (array builders) and #554 (sets and sorting). It also adds the `[~, i] = f(...)` output placeholder, which every set idiom relies on.

## First principles
- **One module.** `libs/array_builtins.py` registers with `setdefault`, so builtins that already exist (`kron`, `horzcat`, `vertcat`, `cat`) keep their tested behaviour. `unique` is wrapped: numeric input without `'stable'`/`'last'` still goes to the existing implementation (#270), and the new path handles cellstr, char, `'stable'` and `'last'`.
- **One set engine for three element kinds.** Numeric, char (by code) and cellstr (by text) inputs are flattened column-major into keys. Sorted output orders by key. `'stable'` orders by first occurrence (A before B for union/setxor). Index outputs are 1-based columns.
- **MATLAB shape rules.** The result is a row when every non-empty input is a row; otherwise it is a column. `setdiff` follows A. Cellstr results follow the same rule.
- **NaN.** Each NaN is distinct (`union([NaN 1], NaN)` has two NaNs) and sorts last. `isequaln` treats NaN as equal.
- **Class.** An integer input class wins (`intersect(int8, double)` is int8), as in MATLAB.
- **sortrows.** It does stable passes from the last key to the first. A negative column or `'descend'` reverses that column, with NaN first when descending (MATLAB). An invalid column errors with `MATLAB:sortrows:COLmismatchX`.
- **`~` outputs.** The parser accepts `~` as a multi-assign target only when a `,` or `]` follows it, so `[~1, 0]` is still logical not. The evaluator discards that output.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| `[~1, 0]` is still a matrix | Still a matrix. Covered by a test. |
| NaN in sets and in sortrows (both orders) | Distinct values, placed last (first when descending). Covered by a test. |
| Mixed-type `cell2mat`; cells of cells | Errors with MATLAB IDs. Covered by a test. |
| `sub2ind`/`ind2sub` out of range | Errors with MATLAB IDs. Covered by a test. |
| Empty operands (`ismember(3, [])`, `setdiff({'a'}, {})`) | Correct empty or false result (probed). |
| `unique(x, 'bogus')` | Errors with "unknown option". Covered by the approved test. |

## Existing-test change (user-approved)
`tests/unit/test_unique_rows.py::test_unique_unknown_option_errors` used to assert that `'stable'` errors. Because `'stable'` is valid MATLAB (documented in `unique`), the test now uses `'bogus'`, and a positive `'stable'` test was added. The user approved this explicitly on 2026-10-13.

## Residuals
#585.
