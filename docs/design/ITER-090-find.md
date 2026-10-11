# Design: find (Issue #90)

**Epic:** #87 · Absorbs part of #73

## Decision
- Nonzero test: `x != 0` and not NaN (NaN is “not found”, like MATLAB for real).
- `find(X)` → **column** vector of 1-based **column-major** linear indices.
- `find(X, k)` → first `k` indices (`k` scalar ≥ 0); `k=0` → empty.
- `nargout=2` → `[r, c]` row/col 1-based (columns).
- `nargout=3` → `[r, c, v]` with values.
- Empty input / no hits → empty 0×1 columns (or 0×0 if nothing).

## Non-goals
`find(X,k,'last')` / `'first'` string flags, sparse.
