# Architecture Notes

## Product intent

OpenMATLAB aims to cover **core MATLAB-like user needs**: a **matrix-first** scientific computing workbench, **interactive** try / plot / tweak, then domain algorithms (toolbox-style libraries). It is **not** a general software-engineering platform.

It is a **clean-room** project driven by public language docs and Octave-compatible ideas where they match documented MATLAB semantics. **No** reverse engineering of proprietary MATLAB binaries or internals.

## Adversarial takeaways (current code vs real use)

The v0.0.1 tree (`lexer` → `parser` → AST → `evaluator` → CLI) is a valid **language spike**, but several choices fight the product goal if left unchanged:

| Risk | Why it hurts |
|------|----------------|
| **Value model = `float`** (`Env = dict[str, float]`) | MATLAB is array-first; scalars are 1×1. Hard-coding `float` forces a rewrite of evaluator, display, and APIs when matrices arrive. |
| **`*` = scalar multiply only** | Public MATLAB: `*` is matrix product; `.*` / `./` / `.^` are element-wise. Grammar must reserve these early. |
| **No matrix syntax in the language layer** | `[...]`, indexing `A(i,j)`, colon `1:n`, transpose `'` are **language**, not a later “math library”. |
| **`;` only as separator** | Interactive MATLAB uses `;` to **suppress display**. REPL workbench UX needs display policy, not just statement breaks. |
| **Flat `dict` workspace** | No base vs function frames, no search path, no `function` M-files → scripts/toolboxes cannot grow cleanly. |
| **Roadmap “runtime done”** | Scalar eval ≠ MATLAB runtime. Treat current runtime as **prototype only**. |
| **Plotting as last layer** | Product needs interactive plot hooks early (host display service), even if backends stay thin. |

**Far future / non-goal for now:** Simulink-class block diagrams, exact MathWorks toolbox parity, MEX/binary plugin compatibility.

## Calibrated target architecture

Grow by adding seams; keep the recursive-descent front-end if it stays maintainable.

```
┌─────────────────────────────────────────────────────────┐
│  Host / Workbench                                         │
│  CLI · REPL · (later: notebook / GUI)                     │
│  Display policy: semicolon suppress, ans, pretty-print    │
│  Plot surface: figure/axes hooks → backend adapter        │
└───────────────────────────┬─────────────────────────────┘
                            │ eval / display requests
┌───────────────────────────▼─────────────────────────────┐
│  Language front-end                                       │
│  lexer → parser → AST (extend, don’t fork)                │
│  + matrix literal, index, colon, transpose, ./.*          │
│  + control flow, function defs (public syntax)          │
└───────────────────────────┬─────────────────────────────┘
                            │ AST / statements
┌───────────────────────────▼─────────────────────────────┐
│  Runtime                                                  │
│  Value: Array-first (numeric ndarray; scalar = 1×1)     │
│  Workspace: base + call frames                            │
│  Function resolve: builtins → path → .m files             │
│  Evaluator (AST walk now; bytecode optional later)        │
└───────────────┬─────────────────────────┬───────────────┘
                │                         │
┌───────────────▼──────────┐  ┌───────────▼───────────────┐
│  Numerics (core math)      │  │  Graphics                  │
│  Array ops, linalg         │  │  plot/plot3/... API        │
│  Impl detail: NumPy/SciPy  │  │  Adapter: matplotlib/etc.  │
│  OK — not MATLAB binaries  │  │  Values stay runtime objs  │
└────────────────────────────┘  └───────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────┐
│  Libraries / “toolboxes” (later)                          │
│  Collections of .m + optional Python accel on same path   │
└──────────────────────────────────────────────────────────┘
```

### Module map (target vs now)

| Area | Target modules / seams | Today (`src/openmatlab/`) |
|------|------------------------|---------------------------|
| Front-end | `lexer`, `parser`, `ast_nodes` | Present — scalar subset only |
| Runtime | `values` (Array), `workspace`, `evaluator`, `functions` | `evaluator` only; `float` env |
| Numerics | `numeric` / thin wrappers over ndarray | Missing |
| Host | `cli`, `display`, `repl` | `cli` + `__main__` only |
| Graphics | `graphics` + backend adapter | Missing |
| Libs | `+path` packages | Missing |

### Critical interfaces (keep stable)

1. **`Value`** — opaque runtime value; numeric arrays are the default; do not leak bare `float` in public eval APIs long-term.
2. **`Workspace`** — get/set/clear; nestable frames for functions.
3. **`FunctionRegistry` / path** — resolve name → callable (builtin or parsed `.m`).
4. **`DisplayHook`** — given value + “suppress?” (semicolon), print or plot.
5. **`NumericBackend`** — create arrays, matmul, element-wise, linalg; NumPy allowed as implementation.

## Current implementation (scalar spike)

| Module | Role |
|--------|------|
| `lexer.py` | Tokenize numbers, idents, operators, `( )`, `=`, `;`, newlines, `%` comments |
| `parser.py` | Recursive-descent → AST (`Number`, `Name`, `BinOp`, `UnaryOp`, `Assign`, `ExprStmt`) |
| `ast_nodes.py` | Frozen AST dataclasses |
| `evaluator.py` | Evaluate AST against `dict[str, float]` |
| `cli.py` / `__main__.py` | REPL, `-e`, script file |
| `__init__.py` | Exports `__version__`, `parse`, `run` |

Precedence today: `*` `/` tighter than `+` `-`; unary `+`/`-`; parentheses group.

**Status label:** language + runtime spike (scalars). **Not** product MVP.

## Layer status (calibrated)

| Layer | Role | Status |
|-------|------|--------|
| **Parser** | MATLAB-like syntax from public docs | Minimal scalar subset done; matrix/index/colon/`.*` **required next** |
| **Runtime** | Values, workspace, call/path | Scalar prototype only; **Array-first + Workspace** next |
| **Core math** | Arrays, linear algebra | Not started (depends on Value/Array) |
| **Host display + plots** | Interactive workbench | REPL exists; display policy + plot adapter **MVP-critical** |
| **Toolboxes** | Domain algorithms | Later (needs path + functions) |
| **Simulink-class** | Block diagrams | Explicit non-goal / far future |

## MVP sequence (recommended)

1. **Array-first `Value` + Workspace** — migrate evaluator off `float`; scalars as 1×1.
2. **Matrix language** — `[ ]`, `;` inside literals vs statement `;`, indexing, colon, `'`, `.*` `./` `.^`, `*` as matmul.
3. **Display policy** — `;` suppresses; `ans`; matrix pretty-print.
4. **Thin numerics** — NumPy-backed ops + a few builtins (`zeros`, `ones`, `eye`, `size`).
5. **Plot MVP** — `plot(x,y)` → matplotlib (or similar) via display/graphics adapter.
6. **Scripts + `function` files + path** — unlock real workflows and later toolboxes.

## Compatibility stance

- Target: behavior as described in **public** language/docs
- Octave-compatible ideas OK where they match public MATLAB semantics
- Exact bit-for-bit / toolbox / Simulink parity is **not** an early goal
- Using open numeric/plot stacks (e.g. NumPy, Matplotlib) as **backends** is fine and is not reverse engineering MATLAB

## Non-goals (architecture)

- No reverse engineering or decompilation of proprietary MATLAB binaries
- No use of RE tools (IDA, Ghidra, Hopper, etc.) against MATLAB
- No dependency on proprietary MathWorks runtime components
- Not a drop-in replacement for MathWorks MATLAB products
- Not a general-purpose software-engineering IDE/platform
- Simulink-class simulation environments: out of scope near-term
