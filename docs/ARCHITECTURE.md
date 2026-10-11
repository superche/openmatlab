# Architecture Notes

## Clean-room approach

OpenMATLAB is a **clean-room** project. Implementation is driven solely by:

- Public MATLAB language documentation and published language behavior descriptions
- Public specifications and Octave-compatible ideas where they align with documented MATLAB semantics
- Independent design of parser, runtime, and libraries

**We do not** reverse-engineer proprietary MATLAB binaries, object code, or closed-source internals.

## High-level layers (planned)

| Layer | Role |
|-------|------|
| **Parser** | Tokenize and parse MATLAB-like source from public grammar/docs |
| **Runtime** | Evaluate AST / IR; manage scopes, arrays, and control flow |
| **Core math** | Numeric arrays, linear algebra, common math builtins |
| **Plotting** | Optional visualization on top of the runtime |

## Compatibility stance

- Target: language and API behavior as described in public docs
- Octave-compatible patterns may inform design where they match public MATLAB semantics
- Exact bit-for-bit parity with MathWorks MATLAB is not a stated goal of early versions

## Non-goals (architecture)

- No binary analysis or decompilation of MATLAB
- No dependency on proprietary MathWorks runtime components
