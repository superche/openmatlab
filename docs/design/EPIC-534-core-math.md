# Design: Epic #534, core math, statistics, random numbers, timing (M7 C05)

Covers #550 (number theory and difference ops), #551 (statistics core) and #552 (random numbers and timing). It also closes the everyday numeric gaps found while working on M7: `isnan`/`isinf`/`isfinite` (found missing during Epic #533), degree trig, vector products, polynomials, filters, interpolation, histogram/accumarray, and fzero/fminsearch/integral.

## First principles
- **One module, registered before the class wrappers.** `libs/math_builtins.py` is registered ahead of `class_builtins`. Its existing single-class wrappers (`diff`, `cumprod`, `fix`, `rem`, …) therefore apply, and a single input keeps class single.
- **Integer classes follow MATLAB.** The computation is done in double, then rounded and saturated back to the class: `cumprod(int8(...))` stops at 127, and `rem(int8,int8)` stays int8.
- **Dimension rules.** The default is the first non-singleton dimension. An explicit `dim` is 1-based, and `'all'` is supported. Empty input to a reduction gives NaN, as in MATLAB.
- **var/std.** `w = 0` normalises by N-1 and `w = 1` by N, or a weight vector can be given. A single sample has variance 0. `'omitnan'` is supported.
- **Random numbers are bit-compatible where it matters.** MATLAB's default generator is Mersenne Twister with `genrand_res53` doubles. `rng(0)` and `'default'` correspond to MT seed 5489, and any other seed is used directly. NumPy's `RandomState` implements the same algorithm.
  - `rng(0); rand(2)` gives MATLAB's well-known `0.8147 0.9058 0.1270 0.9134`. Arrays are filled in column-major order.
  - `s = rng` and `rng(s)` round-trip the full MT state.
  - `randn` keeps the right distribution but not MATLAB's ziggurat values (residual).
- **Timing.** `tic` with an output returns a uint64 id, and `toc(id)` works. Statement forms of `tic`, `toc` and `rng` run with `nargout = 0`: `toc` prints `Elapsed time is … seconds.` and `tic`/`rng` print nothing.
- **Bare-name calls keep their real errors.** `e = toc;` without a `tic` now reports MATLAB's TOC error. It used to say "Undefined variable". The evaluator re-raises when the name is a callable function.
- **Algorithms:**
  - `filter` uses direct form II transposed (MATLAB's), with initial and final conditions.
  - `fzero` searches for a bracket, then runs Brent's method.
  - `fminsearch` is Nelder-Mead with MATLAB's initial simplex (5%, or 0.00025 for zeros).
  - `integral` is adaptive Gauss-Kronrod 7/15, with a variable transform for infinite limits.
  - `round(x,n)` guards against representation error, so `round(2.675,2)` is 2.68.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| `rem(x,0)`, `rem(x,Inf)`, negative operands | NaN; x; the sign of the dividend. Covered by a test. |
| Integer overflow in `cumprod` | Saturates. Covered by a test. |
| `std`/`var` on a scalar, on empty input, or with an invalid `w` | 0, NaN, and an error. Covered by a test. |
| `median` with NaN | NaN unless `'omitnan'`. Covered by a test. |
| `mode` ties | The smallest value wins. Covered by a test. |
| Same seed gives the same stream, and `rng(s)` restores mid-stream | Covered by a test with MATLAB's published values. |
| `sind(180)` returning 1.2e-16 | Exact zeros at multiples of 180 (and `cosd` at odd multiples of 90). Covered by a test. |
| `factorial(171)` | Inf, as in MATLAB. Negative input is an error. |
| `fzero` without a sign change | MATLAB's error. Covered by a test. |
| `nthroot(-16,4)` | MATLAB's error. `nthroot(-27,3) = -3` exactly (Newton correction). |
| `toc` before `tic` hidden as "Undefined variable" | Fixed in the evaluator Name path. All 1239 tests pass and no existing test changed. |
| Gaps | randn/randi stream parity, prctile/quantile, interp1 spline, solver options and histc are filed as **#581**. |
