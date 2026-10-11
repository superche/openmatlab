# Design: script .m parse + eval (Issue #35)

**Epic:** #33 · **KISS**

## Decision
- `.m` with a single top-level `FunctionDef` → function (existing).
- `.m` with only non-function statements → `Script(body=…)`.
- Mixed function+script in one file → error (MVP).
- `eval_script(script, evaluator)` runs body in the **caller Evaluator workspace** (MATLAB-like script shares base WS).

## Non-goals
`run` builtin / path name invoke → Issue #36. Nested functions. `classdef`.
