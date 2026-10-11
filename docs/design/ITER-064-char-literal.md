# Design: single-quote char + transpose disambiguation (Issue #64)

**Epic:** #63 · **KISS / public MATLAB doc semantics**

## Decision
- Lexer is context-sensitive on `'`:
  - If the previous emitted token is a **value-ender** → `TRANSPOSE`
  - Otherwise → char literal (`TokenType.CHAR`), closed by `'`; `''` → one `'`
- Value-enders: `NUMBER IDENT STRING CHAR RPAREN RBRACKET RBRACE TRANSPOSE CTC_TRANSPOSE KW_END`
- Newlines between value and `'` still allow transpose (same as MATLAB line continuation rules for postfix — we keep last non-NEWLINE token).
- Parser: `CHAR` → existing `StringLiteral` AST (same as double-quoted); evaluator already yields `CharValue`.
- `.'` remains `CTC_TRANSPOSE` (unchanged).
- Double-quoted `"..."` unchanged (`STRING`).

## Non-goals
`string` class distinct from char; `'A'+1` char arithmetic; horizontal char concat `[a b]` of chars (may land with cells later).
