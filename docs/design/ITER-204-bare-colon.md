# Design: bare colon in indexing (Issue #204)

**Epic:** #203 · Absorbs #191 · M2 C02

## Decision
- Parse: inside `_in_subscript`, leading `:` → `ColonExpr(start=None, stop=None)` (“all”).
- Eval in `_eval_subscripts`: bare colon → `1:end_val` via `numerics.colon` (linear: numel; 2-sub: shape[i]).
- Works for read and assign (existing range `set_index`).

## Non-goals
3-D `A(:,:,k)`, logical index, `A(i:)` incomplete ranges.
