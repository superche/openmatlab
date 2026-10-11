# ITER-004 Design: Evaluator + DisplayPolicy (draft)

**Issue:** #4 · Depends on: #2 Array, #3 parser

## Goal

Walk AST from `lang.parse` against `Session` (Workspace + `NumPyArrayBackend`)
and print via `DisplayPolicy` (`;` → suppress, bind `ans`).

## Plan (KISS)

1. `runtime.Evaluator.eval_source(source)` → `parse` → eval stmts
2. `MatrixLiteral` → `backend.from_nested` (eval cells first)
3. `BinOp("*")` → `matmul`; `".*"` `"./"` → elem ops; `+` `-` → add/sub
4. `ColonExpr` / `IndexExpr` / `TransposeExpr` → backend helpers (add thin
   methods if missing: `colon`, `subsref`) — keep numerics API small
5. `host.cli` `-e` / REPL call evaluator; `NullDisplay` → real pretty printer
6. Tests: unit eval + Gherkin; **do not** weaken parser tests

## Non-goals

Full `function` files (#6), plot (#5), strings/cells.

## Adversarial watch

- Keep eval out of `lang/`
- No float-dict regression
- Index vs call: treat `IndexExpr` as subsref for arrays; builtins later
