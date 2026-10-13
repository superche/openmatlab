# Design — Epic #482 string arrays and string methods

## First principles
- **One scalar type, one array type.** A 1x1 non-missing string stays a
  `StringValue` (a `CharValue` subclass), so every text consumer from Epic #457
  (flags, `switch`, `which`, `run`) keeps working unchanged. Any other shape,
  or a missing scalar, is a `StringArray`: an immutable 2-D NumPy object grid
  of `str`, with `None` for `<missing>` (`runtime/string_array.py`).
- **Grid in, grid out.** `to_grid(v)` converts a string, a char row (one
  element), a char matrix (one element per row), numbers (`string(x)` text) or
  cellstr. `make(grid)` returns the right type. Every string operation goes
  through these two functions.
- **No second indexing engine.** `s(...)` indexes a position map (`1..n`
  column-major) with the existing numeric `index`/`set_index` paths, then
  gathers. `end`, logical masks, colon, growth (0 → `<missing>`), deletion and
  MATLAB bound errors all come from the numeric path for free.
- **Methods keep the input kind.** string in → string out, char in → char out,
  cellstr in → cell out (`libs/string_builtins.py`).

## Rules (MATLAB)
| Case | Rule |
|------|------|
| `["a" 'bc' 3]` | char becomes one element, numbers convert, `[]` is skipped |
| `s(4) = "d"` on 1x2 | grows, and the gap is `<missing>` |
| `s(i) = []` / `s(:) = []` | deletes / gives 0x0 |
| `s{k}` | the element as a char vector; a missing element is an error |
| `s + t`, `s == t` | elementwise with scalar expansion; `<missing>` propagates through `+`, compares false (`~=` true) |
| `for w = s` | iterates columns |
| `char(s)` | char matrix padded with blanks, column-major order |
| `split(str)` | whitespace by default; `CollapseDelimiters` defaults to true; char input gives a cell |
| `join(s)` | delimiter `" "`; a matrix joins along dim 2 |
| `strcmp(non-text, x)` | false, not an error |
| display | `  RxC string array`, then left-aligned quoted columns, 4-space gutter; `  0x3 empty string array` |

## Behaviour change
`["a" "b"]` used to raise "string arrays are not supported yet". It now builds
a 1x2 string array. One existing test asserted that rejection, and it was updated
(see the acceptance package).

## Adversarial review (done before PR)
| Probe | Finding |
|-------|---------|
| `b = a; b(1) = "z"` | `a` unchanged (immutable grid) ✓ |
| `s(2) = {1}` | MATLAB-style "Conversion to string from cell is not possible." ✓ |
| `s(5)` on 1x2 | numeric-path wording "Index must not exceed 2." ✓ |
| `["a" "b"] + ["a" "b" "c"]` | "Arrays have incompatible sizes for this operation." ✓ |
| `["a" "b"] * 2`, `- 1` | operator error, same as scalars ✓ |
| `t(3)="c"; upper(t)`, `contains(t,…)`, `strlength(t)` | missing propagates / false / NaN ✓ |
| `switch "b"`, `which("zeros")` | still work (scalar stays StringValue) ✓ |
| `{["a" "b"]}` display | `[1x2 string]` summary ✓ |
| `s(1:2)` with a single hit | collapses to a `StringValue` scalar ✓ |

## Non-goals → residual issue #483
N-D string arrays, `missing`/`ismissing`, `compose`/`sprintf`, the regexp
family, `extractBetween`/`insertAfter`/`pad`/`reverse`, `sort`/`unique` on
string arrays, `split` of non-scalar string arrays, and `num2str`/`str2double`
on arrays.

## Number-to-text decisions (#505)
- `num2str` on a non-integer matrix follows MATLAB's rule. Each element is
  formatted with `%<w>.<d>g`, where `d = clamp(floor(log10(max|x|)) + 5, 5, 16)`
  (or the given precision) and `w = d + 7`, plus 1 when any element is
  negative. Blank columns common to all rows are then trimmed. That is why
  `num2str([pi 2*pi])` is `3.1416      6.2832`.
- `sprintf` ties: we keep C `printf` semantics, which round half-even on the
  exact binary value (glibc, as MATLAB does on Linux). `sprintf('%.1f', 2.25)`
  gives `2.2`. This is pinned by `tests/unit/test_num2str_layout.py`.
