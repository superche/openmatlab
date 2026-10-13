# EPIC-626: polynomials and interpolation (M3-E2)

Criterion **T02** (`m3_t02_poly_interp`) in [M3](../milestones/M3-domain-toolboxes.md). The code is in core, in `openmatlab/libs/interp.py`.

## What it covers
- **`spline(x, y[, xx])`**
  - Uses MATLAB `spline.m` not-a-knot end conditions, solving for slopes with Hermite pieces.
  - Two points give a line; three points give the interpolating parabola.
  - `numel(y) == numel(x) + 2` gives a clamped spline whose first and last values are the end slopes.
- **`pchip`**: Fritsch–Carlson harmonic-mean interior slopes and MATLAB's shape-preserving three-point end slopes.
- **pp structs**: `form`, `breaks`, `coefs`, `pieces`, `order`, `dim`. `ppval` evaluates with Horner on the local variable and extrapolates with the end pieces. `mkpp` and `unmkpp` are included.
- **`interp1`** methods `'spline'`, `'pchip'` and `'cubic'` (`'cubic'` means pchip, as in current MATLAB).
  - These methods extrapolate by default, as MATLAB does; a numeric extrapval overrides that.
  - The other methods are delegated unchanged to the existing core `interp1`.
- **`interp2`**
  - Accepts `interp2(Z, Xq, Yq)` and `interp2(X, Y, Z, Xq, Yq[, method[, extrapval]])`.
  - X and Y may be meshgrid matrices or vectors.
  - Methods are linear and nearest; points outside the grid give NaN unless an extrapval is given.
  - A row Xq with a column Yq forms a grid.
- **`polyder`**: `polyder(p)`, the product form `polyder(a, b)`, and the quotient form `[q, d] = polyder(b, a)`. Leading zeros are trimmed.
- **`polyint(p[, k])`**

## Not yet
- vector-valued (matrix y) splines
- `interp2` cubic/spline
- `makima`

These are tracked as residuals on 649.
