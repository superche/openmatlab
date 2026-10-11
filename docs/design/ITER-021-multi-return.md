# Design: multi-return `[a,b] = f(...)` (Issue #21)

**Epic:** #19 · **KISS / AGENTS.md**

## Decision
- New stmt `MultiAssign(names, value, suppress)` — keep single `Assign` unchanged.
- Parse: `[idents] = expr` when `[` … `]` is a name-list then `=`; else rewind to matrix/expr.
- RHS must be a call form (`IndexExpr`/`CallExpr` on unbound name); `nargout = len(names)`.
- `MFileCallable` already slices outputs by `nargout`.
- Display: print each bound name when not suppressed; `ans` = first output.

## Non-goals
`[a,b] = deal(...)`, `~` ignored outputs, multi-assign from non-calls, cell expansion.
