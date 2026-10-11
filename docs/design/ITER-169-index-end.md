# Design: end in indexing (Issue #169)

**Epic:** #168 · Absorbs #163

## Decision
- AST: `EndExpr` marker.
- Parser: while `_in_subscript > 0` (bumped in `_parse_arg_list`), `KW_END` → `EndExpr` (not block closer).
- Evaluator: `_end_stack`; for each subscript `i` of target Array:
  - 1 subscript → `end = numel`
  - 2 subscripts → `end = shape[i]`
- `end-1` works via normal BinOp over EndExpr.
- Assign path uses same resolution before `set_index`.
- Bare `end` outside subscript → ParseError (or EvalError if somehow present).

## Non-goals
Logical LHS, `A(i)=[]`, N-D `end` beyond 2-D.
