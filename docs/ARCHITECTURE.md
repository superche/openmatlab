# Architecture Notes

## Product intent

OpenMATLAB is a **matrix-first** MATLAB-compatible scientific workbench:
interactive try / display / plot / tweak, then domain libraries (toolbox-style).
**Not** a general software-engineering platform.

**Clean-room / public specs only.** No reverse engineering of proprietary
MATLAB binaries or internals. Open stacks (NumPy, Matplotlib, …) as backends
are allowed.

## Stage

**Post-MVP (v0.0.2+):** Epics [#1](https://github.com/superche/openmatlab/issues/1), [#19](https://github.com/superche/openmatlab/issues/19), [#33](https://github.com/superche/openmatlab/issues/33) (scripts + while/break), [#43](https://github.com/superche/openmatlab/issues/43) (core numeric builtins, incl. max/min default omitnan), [#63](https://github.com/superche/openmatlab/issues/63) (single-quote char + cells).
Seams remain Protocol-first; language is a **matrix+procedural MVP**, not full MATLAB.

Acceptance: [`EPIC-001`](acceptance/EPIC-001.md) · [`EPIC-002`](acceptance/EPIC-002.md) · [`EPIC-003`](acceptance/EPIC-003.md) · [`EPIC-004`](acceptance/EPIC-004.md) · [`EPIC-005`](acceptance/EPIC-005.md).

What works today:

- Concrete `NDArrayValue` + `NumPyArrayBackend` (scalar = 1×1)
- Lexer/parser: matrix literals, indexing, colon, transpose, `*` matmul vs `.* ./ .^`, `function`/`end`
- `Evaluator` on `Session` + `ConsoleDisplay` (`;` suppress, `ans`)
- CLI: `openmatlab -e "…"`, bare REPL, QA subcommands (`status` / `features` / `cases` / `defects` / `test`)
- Plot MVP: builtin `plot` / `show`/`drawnow` → `PlotSurface` → Matplotlib (**Agg** default; interactive via env)
- `.m` functions: `ToolboxPath.find_mfile` → `FunctionResolver` load/cache → call from evaluator
- `while`/`break`; script `.m` via `load_mfile`/`eval_script` + language `run("…")`
- Single-quoted char literals (context-sensitive vs transpose) + cell `{…}` / `c{i}` / `cell(m,n)`
- Numeric builtins toolbox (`libs/numeric_builtins.py` → `FunctionResolver.builtins`): zeros/ones/eye/linspace, size/numel/length, sum/prod/mean/min/max, abs/sqrt/exp/log/sin/cos/floor/ceil/round/mod; `nan`/`NaN`; max/min default omitnan

Residual non-parity (later): `continue`, rich toolboxes, bare script name without `run`, full interactive GUI tweak loop.
Residual after Epic #5: see Issues on #63 (assignment, cellfun, string class, …).

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
    numeric_builtins.py core numeric builtins (elmat / reductions / elfun / cell)
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

**Parsed + evaluated:** numbers, single- and double-quoted chars, cell `{…}`, names, `+ - * /` and `.* ./ .^`, unary `±`,
`[rows]`, `A(i,j)`, `a:b` / `a:s:b`, `A'` / `A.'`, assignments, `;` suppress,
`function [outs]=name(ins) … end` in `.m` files on the path,
language `addpath("…")` / `which("…")`, multi-return `[a,b]=f(...)`,
`if`/`elseif`/`else`/`for`/`end`, builtins `plot` / `show` / `drawnow`.

**Not yet:** `continue`, cell assignment/`cellfun`/`string` class,
scripts without `function`, nested functions, `nargin`/`nargout` specials.

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
