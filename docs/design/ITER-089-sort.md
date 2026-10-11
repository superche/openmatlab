# Design: sort + [B,I]=sort (Issue #89)

**Epic:** #87 · Absorbs part of #73

## Decision
- Ascending only. `sort(A)` / `sort(A, dim)` — default first non-singleton dim.
- `[B, I] = sort(...)` — `I` is 1-based index of arrangement along the sort axis (`np.argsort` + 1).
- Shape preserved. `dim > ndim` → identity + ones indices.
- NaNs sort to the end (NumPy default / MATLAB-compatible-ish for real).

## Non-goals
`'descend'`, `'ComparisonMethod'`, `issorted`.
