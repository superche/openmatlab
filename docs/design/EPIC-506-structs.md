# Design — Epic #506 structs

## First principles
- **One value type.** `StructValue` (`runtime/struct_value.py`) is an immutable
  2-D array of records that all share one ordered field list. Elements are
  stored column-major. A scalar struct is simply 1x1, as in MATLAB. It is
  deliberately *not* an `Array`, so numeric code never mistakes it for numbers.
- **Reuse index semantics through a position map.** `s(idx)`, `s(idx) = t`,
  growth, `s(idx) = []` and `end` run on a double array holding `1..numel` in
  the struct's shape. That array goes through the existing numeric
  `index`/`set_index`, and the records follow the positions. Zeros created by
  growth become new elements whose fields are all `[]`. No index rule is
  duplicated.
- **Chained assignment is a recursive walk.** `ChainAssign` (parser) covers any
  left-hand side with a field, or with nested `()`/`{}` steps. Each step reads
  the current child, recurses, then writes it back. Field steps create a struct
  from nothing or from `[]`. A `()` step on a struct targets one element and
  grows the array when needed. A `()`/`{}` step on a non-struct runs the
  existing `ArrayAssign`/`CellAssign` code against a temporary variable, so
  numeric growth, cell growth and `end` behave exactly as they already did.
- **Cs-lists are an evaluator-only value.** `s.f` on a non-scalar struct
  yields a `CsList`. List contexts (`[...]`, `{...}`, call arguments) expand it.
  A bare statement shows each value as `ans`. Other contexts take the first
  value.
- **Lexer.** `.` becomes a `DOT` token only right after an identifier, `)` or
  `}`, with no space before it, and followed by a letter, `_` or `(`. As a
  result `a.'`, `.*`, `[a .5]` and `1.5` keep their meaning.

## Display (MATLAB)
```
s =

  struct with fields:

      a: 1
    bcd: 'hi'
      m: [2×2 double]
      c: {1×2 cell}
      n: [1×1 struct]
```
Arrays print `1×2 struct array with fields:` followed by the names, and an
empty array prints `0×0 empty struct array with fields:`. A struct with no
fields prints `struct with no fields.`, and a struct inside a cell prints as
`[1x1 struct]`.

## Adversarial review (done before PR)
| Probe | Finding |
|-------|---------|
| `x = []; x.a = 1` | becomes a struct ✓ |
| `x = 5; x.a = 1` | MATLAB error ✓ |
| `s = struct('a',{1,2}); s.a = 3` | "Scalar structure required" ✓ |
| `s(2) = struct('b',1)` with field `a` | "dissimilar structures" ✓ |
| `s(3).a = 5` on undefined `s` | 1x3, and `s(1).a` is `[]` ✓. This exposed an existing bug: `x = []; x(3) = 1` gave 3x1. It now gives 1x3, as in MATLAB (no existing test asserted the old shape) |
| `s.('1bad') = 1` | "Invalid field name" ✓ |
| `max(s(1:2).a)` | the cs-list expands into arguments, so it is `max(4,5)` ✓ |
| `c{2}.x = 4`, `s.c{3} = 'x'`, `q.w{3}.z = 'k'` | mixed chains grow ✓ |
| `[a .5]`, `a.'`, `b.^2` | lexer unaffected ✓ |
| `[q, w] = s.a` | not supported (cs-list multi-assign); residual |
| `disp(s)`, `isrow` | `disp` and `isrow` are not implemented for any type; residual |
| field row display `[1.5000 2.0000]` | MATLAB prints `[1.5000 2]`; cosmetic residual |

## Non-goals → residual issues
N-D struct arrays, `[a, b] = s.f` and `[s.f] = deal(...)`, `arrayfun`/`structfun`,
`struct2cell`/`cell2struct`, `disp`, and per-element short-g formatting in field
summaries.
