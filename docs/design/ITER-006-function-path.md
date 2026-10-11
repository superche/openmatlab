# ITER-006 Design: ToolboxPath + .m function load/eval

**Issue:** #6 · **Principles:** AGENTS.md (KISS)

## Done (slice 1)
- `ToolboxPath.find_mfile`
- `FunctionResolver.which` path hits

## This slice (complete #6 MVP)

1. Lexer: `function` / `end` → `KW_FUNCTION` / `KW_END`
2. Parser: `FunctionDef` (`function [outs]=name(ins) ... end`)
3. `parse_mfile` + `MFileCallable` — new workspace, bind inputs, run body, read outputs
4. `FunctionResolver.resolve` loads/caches callables; `bind_runtime(numerics, plots)`
5. Evaluator: unbound `name(args)` → resolver (after `plot` builtin)

## Non-goals
Nested functions, nargin/nargout specials, script .m without `function`, classes.
