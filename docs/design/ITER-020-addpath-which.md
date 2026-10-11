# Design: language `addpath` / `which` (Issue #20)

**Epic:** #19 · **Principles:** KISS / AGENTS.md

## Decision
- Double-quoted strings only (`"dir"`) — avoids clash with `'` transpose.
- `StringLiteral` AST → `CharValue` (implements `Value`, not `Array`).
- Builtins `addpath` / `which` handled in evaluator before FunctionResolver (like `plot`).
- `addpath` → `Session.functions.path.addpath(...)`; returns `CharValue` of resolved dir.
- `which("name")` → `CharValue` of `FunctionResolver.which` result (may be empty).

## Non-goals
Single-quoted char vectors, `genpath`, `rmpath` language form, string arrays.
