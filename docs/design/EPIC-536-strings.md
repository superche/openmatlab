# Design: Epic #536, core strings (M7 C07)

Covers #555 (strsplit, strjoin, strfind, strcat, strvcat, str2num) and #556 (mat2str, int2str, dec2bin, bin2dec, hex2dec, dec2hex, blanks, deblank). It also makes `fliplr`/`flipud`/`flip` work on char and cell arrays.

## First principles
- **New module.** `libs/strfun_builtins.py` registers with `setdefault`. The existing `string_builtins`/`text_builtins` (string class, regexp, num2str, …) are untouched. The flip wrappers register last, so they wrap the numeric implementations instead of replacing them.
- **`strsplit`.** The default delimiter is whitespace and `CollapseDelimiters` defaults to true. Literal delimiters are regex-escaped and the longest one is tried first. `DelimiterType RegularExpression` is supported. Empty edge pieces are kept (MATLAB).
- **`strcat`.** Char inputs lose trailing whitespace. When any input is a cell, the operation is element-wise and nothing is trimmed (MATLAB's documented asymmetry).
- **`str2num`.** It evaluates `[` + text + `]` in a fresh session and returns `ok = false` on any failure. It never raises (MATLAB).
- **`mat2str`.** Default precision is 15 significant digits. Logicals print as `true`/`false`, integer classes print exactly, `'class'` wraps the result in the class name, char is quoted with `''` escapes, and empty input gives `zeros(r,c)`.
- **`int2str`.** It rounds half away from zero, then uses the existing `num2str` integer layout (`'1  4'`).
- **Base conversion.** Values are padded to a common width (char matrix for vector input), the min-digits argument is supported, and invalid digits error with MATLAB IDs.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| Overlapping `strfind('aaa','aa')` | `[1 2]`. Covered by a test. |
| `str2num('1+')`, `str2num('x=3')` | `ok = 0` and empty, with no error leaked. Covered by a test / probed. |
| Wrong number of `strjoin` delimiters | Errors. Covered by a test. |
| Char-matrix `strcat` with trailing blanks | Trimmed per row, then padded. Covered by a test. |
| `bin2dec('12')`, negative `dec2bin` | Errors (negative input is a residual). |
| Existing `string_builtins` name clash | Avoided: new module name. The full suite is green. |

## Residuals
#589.
