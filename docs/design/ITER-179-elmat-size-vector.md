# Design: zeros/ones/eye size-vector form (Issue #179)

**Epic:** #178 · Absorbs #70 · Milestone: Octave-breadth

## Decision
Extend `_shape2` used by `zeros`/`ones`/`eye`/`nan`/`cell`:

| Call | Shape |
|------|--------|
| `zeros` / `zeros()` | 1×1 |
| `zeros(n)` scalar | n×n |
| `zeros(m,n)` | m×n |
| `zeros([m n])` / `zeros([m; n])` | m×n (2-element size vector) |
| `zeros([n])` (1×1 matrix) | n×n (same as scalar `zeros(n)`) |
| `zeros([m n p])` | BuiltinError (N-D deferred #74) |

`eye` uses the same helper → `eye([m n])` yields m×n identity.

## Non-goals
N-D size vectors, `'like'` / class trailing args.
