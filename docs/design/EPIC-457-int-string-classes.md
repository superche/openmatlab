# Design — Epic #457 integer classes, string class, char indexing

## First principles
- **Integers** are `NDArrayValue` buffers with a NumPy integer dtype, and the
  class name comes from the dtype (`numerics/intclass.py`). There is one
  conversion rule: compute in double, then **round half away from zero, map
  NaN to 0, and saturate** (`saturate`). Every integer result goes through it.
- **Strings:** `StringValue` subclasses `CharValue`. Code that only needs text
  (flags, `which`, `run`, `switch`) keeps working unchanged. Only the
  MATLAB-visible behaviour differs: class `string`, size 1x1, `+`
  concatenates, comparisons are textual, display is `"abc"`.
- **Char indexing** maps the char matrix to its code matrix, reuses the
  numeric index/assign/delete/transpose paths, then maps back. There is no
  second indexing implementation.

## Integer rules (MATLAB)
| Case | Rule |
|------|------|
| `int op double` | result has the int class (`_int_result` in `numpy_backend`) |
| `int8 op int16` | error "Integers can only be combined with integers of the same class, or scalar doubles." |
| `intA * intB`, both non-scalar | MTIMES error |
| `x(i) = int8(v)` with `x` double | `x` converts to int8 |
| `[int8 double]`, `[int16 int8]` | leftmost integer class |
| `a:b` with int endpoints, `for` over ints | int class kept |
| `sum/prod/max/min/abs/cumsum/sort/unique` | result keeps the input's int class (`_keep_int`); `mean` gives double |
| display | exact digits, 2-space gutter |

## Constructor class args (#183)
`_peel_class` strips a trailing `'cls'` or `'like', P`:
- `zeros/ones/eye` accept double or any int class.
- `nan/Inf` accept only double; `true/false` accept only logical.
- `'like'` with a complex double prototype gives a complex result.

## Behaviour change
`'a' + 'b'` used to be a hidden concatenation shortcut. It is now numeric `195`, as in MATLAB.
String concatenation is `"a" + "b"`. No existing test relied on the old shortcut.

## Adversarial review (done before PR)
| Probe | Finding |
|-------|---------|
| `int32(Inf)`, `int8(NaN)` | 2147483647 / 0 ✓ |
| `float(iinfo(int64).max)` rounds up to 2^63 | the saturate edge is pinned explicitly |
| `int32(7)/0` | RuntimeWarning noise → suppressed; saturates to intmax ✓ |
| `int8(1):int8(3)` / for loop | var was double → fixed (colon + for keep int) |
| `[1 int16(300); int8(1) 2]` | int16 (leftmost) ✓ |
| `m(:,1)'` on char | transpose rejected CharValue → fixed |
| `"a"*2` | MATLAB-style operator error ✓ |
| `["a" "b"]` | rejected explicitly (string arrays are a residual) instead of silently making `"ab"` |
| `switch "b"` / `which("zeros")` | still work with StringValue ✓ |

## Non-goals → residual issues
String arrays (`["a" "b"]`, `strings(n)`), string methods (`split`, `join`,
`contains`, `replace`…), `single`, `idivide`/`bitand` family, exact int64
arithmetic beyond 2^53, and `[1x2 int8]` summaries inside cell display.
