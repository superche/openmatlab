# Architecture Notes

## Clean-room approach

OpenMATLAB is a **clean-room** project. Implementation is driven solely by:

- Public MATLAB language documentation and published language behavior descriptions
- Public specifications and Octave-compatible ideas where they align with documented MATLAB semantics
- Independent design of parser, runtime, and libraries

**We do not** reverse-engineer proprietary MATLAB binaries, object code, or closed-source internals.

## Current implementation (scalar subset)

| Module | Role |
|--------|------|
| `lexer.py` | Tokenize numbers, idents, operators, `( )`, `=`, `;`, newlines, `%` comments |
| `parser.py` | Recursive-descent → AST (`Number`, `Name`, `BinOp`, `UnaryOp`, `Assign`, `ExprStmt`) |
| `evaluator.py` | Evaluate AST against a `dict` environment (float scalars) |
| `cli.py` / `__main__.py` | REPL, `-e`, script file |

Precedence: `*` `/` bind tighter than `+` `-`; unary `+`/`-` on factors; parentheses group.

## High-level layers (planned)

| Layer | Role | Status |
|-------|------|--------|
| **Parser** | Tokenize and parse MATLAB-like source | Minimal subset done |
| **Runtime** | Evaluate AST; scopes / arrays | Scalars done |
| **Core math** | Numeric arrays, linear algebra | Next |
| **Plotting** | Optional visualization | Planned |

## Compatibility stance

- Target: language and API behavior as described in public docs
- Octave-compatible patterns may inform design where they match public MATLAB semantics
- Exact bit-for-bit parity with MathWorks MATLAB is not a stated goal of early versions

## Non-goals (architecture)

- No binary analysis or decompilation of MATLAB
- No dependency on proprietary MathWorks runtime components
