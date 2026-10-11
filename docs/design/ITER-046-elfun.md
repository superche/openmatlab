# Design: elementwise math builtins (Issue #46)

**Epic:** #43 · **KISS / public MATLAB doc semantics, real domain only**

## Decision
- `abs sqrt exp log sin cos floor ceil round`: one Array arg, shape preserved.
- `round`: half **away from zero** (`sign(x) .* floor(abs(x) + 0.5)`), not NumPy banker's rounding.
- `mod(a, b)`: `a - floor(a./b).*b`; `mod(x, 0) = x`; sign follows divisor. Scalar broadcast; otherwise shapes must match.
- Real domain: `sqrt` / `log` of a **negative** element → `EvalError` (complex results are an
  explicit non-goal; failing loudly beats silently returning NaN). `log(0) = -Inf` allowed.
- Same `libs.numeric_builtins` seam.

## Non-goals
Complex results, `rem`, `fix`, `atan2`, integer-class overflow rules.
