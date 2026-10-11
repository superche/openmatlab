# Architecture Notes

## Product intent

OpenMATLAB is a **matrix-first** MATLAB-compatible scientific workbench:
interactive try / display / plot / tweak, then domain libraries (toolbox-style).
**Not** a general software-engineering platform.

**Clean-room / public specs only.** No reverse engineering of proprietary
MATLAB binaries or internals. Open stacks (NumPy, Matplotlib, …) as backends
are allowed.

## Stage

**Post-MVP (v0.0.2+):** Epic [#1](https://github.com/superche/openmatlab/issues/1) delivered the calibrated fill order.
Seams remain Protocol-first; language evaluation is a **matrix MVP**, not full MATLAB.

Acceptance evidence: [`docs/acceptance/EPIC-001.md`](acceptance/EPIC-001.md).

What works today:

- Concrete `NDArrayValue` + `NumPyArrayBackend` (scalar = 1×1)
- Lexer/parser: matrix literals, indexing, colon, transpose, `*` matmul vs `.* ./ .^`, `function`/`end`
- `Evaluator` on `Session` + `ConsoleDisplay` (`;` suppress, `ans`)
- CLI: `openmatlab -e "…"`, bare REPL, QA subcommands (`status` / `features` / `cases` / `defects` / `test`)
- Plot MVP: builtin `plot` / `show`/`drawnow` → `PlotSurface` → Matplotlib (**Agg** default; interactive via env)
- `.m` functions: `ToolboxPath.find_mfile` → `FunctionResolver` load/cache → call from evaluator

Explicit non-parity (next epics): language `addpath`/`which`, multi-return `[a,b]=f()`, control flow beyond `function`/`end`, interactive (non-Agg) plot, rich toolboxes.

## Package layout

```
src/openmatlab/
  host/           # workbench shell
    cli.py          -e / REPL / QA subcommands
    repl.py         ReplSession → runtime.Session
    display.py      DisplayPolicy (semicolon suppress, ans, pretty-print)
    plot_surface.py PlotSurface → graphics backend
  lang/           # language front-end
    tokens.py       TokenType (matrix + KW_FUNCTION / KW_END)
    ast_nodes.py    AST incl. MatrixLiteral / Index / Colon / FunctionDef
    lexer.py        tokenize() — matrix MVP subset
    parser.py       parse() — matrix MVP + function defs
  runtime/        # execution model
    value.py        Value / Array protocols
    workspace.py    base + nested frames
    functions.py    FunctionResolver + MFileCallable / parse_mfile
    evaluator.py    AST evaluator (Array-first)
    session.py      Session composition root (create_default wires backends)
  numerics/       # array ops behind Array
    backend.py      ArrayBackend protocol
    numpy_backend.py NumPyArrayBackend
    ndarray_value.py NDArrayValue
  graphics/       # plotting backends
    backend.py      GraphicsBackend protocol
    matplotlib_backend.py MatplotlibGraphicsBackend (Agg default)
  libs/           # path / toolboxes
    path.py         ToolboxPath (addpath / find_mfile)
  qa/             # feature_map / catalog / defects→gh bridges
```

## Layer diagram

```
Host (CLI -e / REPL / QA)
       │
       ├── DisplayPolicy ──► pretty-print / ans / ';' suppress
       ├── PlotSurface ──► GraphicsBackend (Matplotlib Agg MVP)
       └── Session ── Workspace + FunctionResolver + ToolboxPath
              │              + ArrayBackend + optional graphics
              ▼
           Evaluator ◄── lang.parser → AST
              │
              └── unbound name(args) → builtins / .m on path
```

## Critical interfaces

| Seam | Role |
|------|------|
| `Value` / `Array` | Array-first runtime values; scalar as 1×1 |
| `Workspace` | Base + call frames (`.m` calls use a fresh workspace) |
| `FunctionResolver` + `ToolboxPath` | builtins → path → `.m` load/eval |
| `DisplayPolicy` | Interactive display; `Assign`/`ExprStmt.suppress` |
| `PlotSurface` / `GraphicsBackend` | Plotting (Agg MVP; interactive later) |
| `ArrayBackend` | matmul / element-wise / literals / index / colon |
| `Session` | Composition root (`create_default` wires NumPy + display + plot) |

## Language coverage (MVP)

**Parsed + evaluated:** numbers, double-quoted strings, names, `+ - * /` and `.* ./ .^`, unary `±`,
`[rows]`, `A(i,j)`, `a:b` / `a:s:b`, `A'` / `A.'`, assignments, `;` suppress,
`function [outs]=name(ins) … end` in `.m` files on the path,
language `addpath("…")` / `which("…")`, `if`/`elseif`/`else`/`for`/`end`.

**Not yet:** single-quoted char vectors/cells, `while`/`break`/`continue`,
multi-assign `[a,b]=f(…)`, scripts without `function`, nested functions,
`nargin`/`nargout` specials.

## Non-goals

- Reverse engineering / decompiling MATLAB; RE tools against MATLAB
- Depending on proprietary MathWorks runtimes
- Drop-in replacement / bit-for-bit / full toolbox parity
- Simulink-class block diagrams (far future / out of scope near-term)
- General software-eng IDE platform

## Adversarial checklist

| Prior risk | Structural mitigation |
|------------|----------------------|
| `float` env | Deleted; `Value`/`Array` + `NDArrayValue` |
| `*` vs `.*` | Distinct tokens + evaluator ops |
| Matrix syntax as “library” | First-class `lang` AST + parser |
| `;` display | `suppress` on stmts + `DisplayPolicy` |
| Flat dict | `Workspace` frames; `.m` isolated WS |
| No plot seam | `PlotSurface` + Matplotlib backend |
| No path/functions | `FunctionResolver` + `ToolboxPath` + `MFileCallable` |
| No composition root | `runtime.Session.create_default` |
| Stale “architecture stage” docs | This file + epic acceptance + feature_map sync chore |

## QA system (five layers, off-the-shelf preferred)

See `docs/QA.md`. After each epic: acceptance evidence + **docs/feature_map sync chore**
before the next epic (`docs/PROCESS.md`).

Status vocabulary (`done` / `partial` / `stub`): see PROCESS § Feature status criteria.
