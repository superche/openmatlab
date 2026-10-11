# Design: bare NaN/Inf/pi (Issue #214)

**Epic:** #213 · Absorbs #192 · M2 C04

## Decision
- `eval_expr(Name)`: workspace hit → value; else `_invoke_call(Name, [], nargout=1)`;
  if that fails → `Undefined variable`.
- Add builtins `Inf`/`inf` (like `nan`) and `pi` (0-arg scalar).
- Workspace assignment still shadows (`NaN = 5`).

## Non-goals
`eps`/`realmax` catalog; complex `i`/`j`.
