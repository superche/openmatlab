# Design: elmat constructors + shape builtins (Issue #44)

**Epic:** #43 · **KISS / clean-room (public MATLAB doc semantics)**

## Decision
- New module `openmatlab.libs.numeric_builtins` owns builtin callables; each matches
  `CallableFunction(args, *, nargout) -> Sequence[Value]`.
- `register_numeric_builtins(resolver)` installs them into `FunctionResolver.builtins`;
  `Session.create_default` calls it when NumPy is available. Evaluator is unchanged
  (unbound `name(args)` already resolves builtins first) — no new evaluator branches.
- Results are always 2-D `NDArrayValue` (`_wrap`: 0-D → 1×1, 1-D → 1×n).
- Size args must be non-negative integer scalars; negative → 0 (MATLAB treats negative dims as 0).

## Builtins
| name | forms |
|------|-------|
| zeros / ones | `f()`→1×1, `f(n)`→n×n, `f(m,n)` |
| eye | `eye()`, `eye(n)`, `eye(m,n)` |
| linspace | `linspace(a,b)` (100 pts), `linspace(a,b,n)` → 1×n |
| size | `size(A)`→1×2; `size(A,d)` (d>2 → 1); `[m,n]=size(A)` |
| numel | scalar count |
| length | max(size) or 0 if empty |

## Non-goals
`zeros([m n])` vector-form, class args (`'int32'`), N-D (>2).
