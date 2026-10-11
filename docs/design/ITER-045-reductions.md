# Design: reductions sum/prod/mean/min/max (Issue #45 + #55)

**Epic:** #43 · **KISS / public MATLAB doc semantics**

## Decision
- Default dim = **first non-singleton** dimension (size ≠ 1); all-singleton → dim 1.
- `f(A, dim)` for sum/prod/mean; `dim > 2` → returns `A` unchanged (2-D MVP).
- Results keep 2-D shape (reduced axis → length 1): vector → 1×1, matrix → 1×n row.
- `0×0` empty input: `sum([])=0`, `prod([])=1`, `mean([])=NaN` (MATLAB special case).
- `max/min(A)`: `nargout 2` → `[m, i]` with **1-based** index of first extremum.
- `max/min(A, B)`: elementwise with scalar broadcast. `max(A, [], dim)` supported.
- **NaN (default omitnan, #55):** reduce forms skip NaN; all-NaN → NaN and `i=1`.
  Two-arg form uses `fmax`/`fmin` (prefer non-NaN; both NaN → NaN).
- Lives in `libs.numeric_builtins`; registered via the same seam as #44.

## Non-goals
Explicit flag strings (`'omitnan'` / `'includenan'` / `'all'`), `cumsum`, complex magnitudes.
