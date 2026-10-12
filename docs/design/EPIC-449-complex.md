# Design — Epic #449 complex numbers

## First principles
MATLAB `double` is real or complex; `class` stays `double`. We store complex
values as NumPy `complex128` in the same `NDArrayValue`, with no new Value type.
One rule keeps results MATLAB-true: **narrowing**. Any computed result whose
imaginary parts are all zero becomes real (`_narrow` in `numpy_backend`, and
`_wrap` in builtins). Only `complex(a,b)` builds complex storage with zero imaginary parts.

## Pipeline
- **Lexer/parser:** a NUMBER followed by `i/j/I/J` and a non-identifier char
  becomes `NumberLiteral(complex(0,x))`. Bare `i`/`j` already resolved to `1i` when unbound.
- **Backend:** `_dt` picks float64/complex128 per operand set. index, set_index,
  grow and concat keep the dtype; element-wise ops, matmul and power narrow results.
- **Power:**
  - A negative real base with a non-integer exponent goes complex (`(-8)^(1/3)`).
  - `A^p` for non-integer or complex `p` uses eig. Round-off imaginary parts below
    1e-10·max|out| are dropped, which unblocks #228's complex results.
  - `s^A` for `s<0` or complex `s` uses `expm(log(s)A)` with noise cleanup.
  - Complex matrices raised to integer powers use `matrix_power` (#229).
- **Elfun:** sqrt/log of negatives promote to complex. floor/ceil/round apply per
  part. mod rejects complex with MATLAB's message.
- **New builtins:** real, imag, conj, angle, complex, isreal.
- **Relational:** `==`/`~=` compare full values; `< <= > >=` compare real parts. Truthiness means nonzero.
- **Extrema/sort:** compare |z|, then angle, as MATLAB does. `'ComparisonMethod','real'` uses real then imag.
- **Display:** format short `3 + 4i`, `1.5000 - 2.0000i`, with per-column alignment of real and imaginary parts.

## Adversarial review (done before PR)
| Probe | Finding |
|-------|---------|
| `3+4i` | used to lex as `3+4` then `i` (=7!) — fixed by the literal suffix |
| `i=5; 2i` | 2i stays imaginary ✓ |
| `(-2)^[1 0;0 1]` | expm left ~1e-16 imag noise that kept the result complex — cleaned → real `[-2 0;0 -2]` |
| `z(2)=1i; z(2)=0` | narrows back to real ✓ |
| `sort([3 1i -2])` | used to sort by real part; now by `|z|` → `[1i -2 3]` |
| `find([0 1i 0])` | cast to float discarded the imaginary part → returned empty; fixed → 2 |
| `mod(1i,2)` | raw NumPy TypeError → MATLAB message |
| `max([1 -3i 2])` | NumPy compares lexicographically; now by magnitude → `-3i` |

## Non-goals → residual issues
Sparse matrices (#229's sparse half), complex `unique`/`issorted`, scaled
complex display (`1.0e+05 *`, large magnitudes), and test coverage for
`sin`/`cos`/`exp` of complex arrays beyond the smoke tests.
