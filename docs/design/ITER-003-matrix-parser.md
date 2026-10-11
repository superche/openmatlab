# ITER-003 Design: Matrix-first lexer/parser

**Issue:** #3 · **Principles:** AGENTS.md (KISS, Occam, deslop)

## Goal

Real `tokenize` / `parse` for a matrix-capable subset. **No evaluator** (#4).

## Surface

| Form | Tokens / AST |
|------|----------------|
| `[1 2; 3 4]` | `MatrixLiteral` rows |
| `A(i,j)` | `IndexExpr` (call vs index deferred to #4) |
| `1:n` / `1:2:n` | `ColonExpr` |
| `A'` / `A.'` | `TransposeExpr` |
| `*` vs `.*` `./` `.^` | `BinOp` with op string |
| `a = expr;` | `Assign`/`ExprStmt` + `suppress` |

## Precedence (simplified public MATLAB-like)

postfix (`'` / `.'` / `(…)`) → power (`^` `.^`) → unary `+`/`-` →
mul (`*` `/` `.*` `./`) → add (`+` `-`) → colon (`:`) →
(statement assign).

## Lexer notes

- Bracket depth: newline inside `[…]` → `SEMICOLON` (row sep)
- Outside: newline → `NEWLINE` (statement sep)
- `'` always transpose this iteration (no char strings yet)
- `%` line comments

## Non-goals

Evaluator, keyword statements (`if`/`function`), cells `{}`, strings.

## Tests

Unit lexer/parser + Gherkin; update architecture tests that expected stubs.
