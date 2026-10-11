# Design: run("script.m") (Issue #36)

**Epic:** #33 · **KISS**

## Decision
- Builtin `run("path")` — double-quoted string.
- Resolve: absolute/relative file if exists; else `ToolboxPath.find_mfile(name)`.
- `load_mfile` must yield `Script` (reject function files with clear error).
- Evaluate via `eval_script` in **current** Evaluator (shared workspace).
- Returns scalar `1` (like show).

## Non-goals
Command-form bare `myscript` without `run`; `run` with options; publishing.
