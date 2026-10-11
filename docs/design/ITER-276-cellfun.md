# Design: cellfun + @function_handle (Issue #276)

**Epic:** #275 · Absorbs #81 · M2 C10 (final)

## Decision
1. Lexer/parser: `@` + IDENT → `FuncHandleExpr(name)`.
2. `FunctionHandleValue(name, fn)` — resolve at handle creation; `matlab_class` = `function_handle`.
3. `cellfun(fh, C)` UniformOutput=true: apply `fn([cell])` per cell; each result must be scalar numeric; assemble same-shaped double array.

## Non-goals
Anonymous `@(x)…`; UniformOutput false; Extra options; char function name (residual OK).
