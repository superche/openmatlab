# Architecture Notes

## Product intent

OpenMATLAB is a **matrix-first** MATLAB-compatible scientific workbench:
interactive try / display / plot / tweak, then domain libraries (toolbox-style).
**Not** a general software-engineering platform.

**Clean-room / public specs only.** No reverse engineering of proprietary
MATLAB binaries or internals. Open stacks (NumPy, Matplotlib, …) as backends
are allowed.

## Stage

**Architecture stage (v0.0.2):** package seams, Protocols/ABCs, stubs, and
reserved grammar/AST forms. **Language evaluation is intentionally incomplete.**
The old scalar `float`-dict evaluator was **removed** so it cannot steer design.

## Package layout

```
src/openmatlab/
  host/           # workbench shell
    cli.py          thin CLI (--status / version; no eval)
    repl.py         ReplSession → runtime.Session
    display.py      DisplayPolicy (semicolon suppress, ans, pretty-print)
    plot_surface.py PlotSurface → graphics backend
  lang/           # language front-end
    tokens.py       TokenType incl. reserved matrix grammar
    ast_nodes.py    AST + MatrixLiteral/Index/Colon/Transpose/FunctionDef
    lexer.py        stub (NotImplementedError)
    parser.py       stub (NotImplementedError)
  runtime/        # execution model
    value.py        Value / Array protocols (scalar = 1×1)
    workspace.py    base + nested frames
    functions.py    FunctionResolver (builtins → path → .m)
    evaluator.py    stub (no float-dict guts)
    session.py      Session composition root
  numerics/       # array ops behind Array
    backend.py      ArrayBackend protocol
    numpy_backend.py placeholder stub
  graphics/       # plotting backends
    backend.py      GraphicsBackend protocol
    matplotlib_backend.py placeholder stub
  libs/           # toolboxes later
    path.py         ToolboxPath (addpath / find_mfile stub)
```

## Layer diagram

```
Host (CLI/REPL) ── DisplayPolicy ──► pretty-print / ans / ';' suppress
       │
       ├── PlotSurface ──► GraphicsBackend (matplotlib stub)
       │
       └── Session ── Workspace + FunctionResolver + ToolboxPath (+ numerics/graphics backends)
              │              │
              │              └── ArrayBackend (NumPy stub)
              ▼
           Evaluator (stub) ◄── lang.parser → AST
```

## Critical interfaces

| Seam | Role |
|------|------|
| `Value` / `Array` | Array-first runtime values; no primary `dict[str, float]` |
| `Workspace` | Base + call frames |
| `FunctionResolver` + `ToolboxPath` | builtins → path → `.m` |
| `DisplayPolicy` | Interactive display; `Assign/ExprStmt.suppress` |
| `PlotSurface` / `GraphicsBackend` | Interactive plotting |
| `ArrayBackend` | matmul / element-wise / literals |
| `Session` | Wires the above for one workbench instance |

## Reserved language forms (not yet parsed)

`TokenType` / AST reserve: `[ ]`, `.* ./ .^`, `\`, `'`, colon, comma,
relational ops, `function` / `if` / `for` / `while` / `end`,
`MatrixLiteral`, `IndexExpr`, `ColonExpr`, `TransposeExpr`, `CallExpr`,
`FunctionDef`. Statement nodes carry `suppress: bool` for `;` display policy.

## MVP implementation order (after architecture)

1. Concrete `Array` + `NumPyArrayBackend`
2. Lexer/parser for matrix literals, indexing, colon, `.*`, `*` matmul
3. Evaluator on `Session` + `DisplayPolicy`
4. Plot MVP via `PlotSurface` + Matplotlib
5. `function` files + path lookup → toolboxes

## Non-goals

- Reverse engineering / decompiling MATLAB; RE tools against MATLAB
- Depending on proprietary MathWorks runtimes
- Drop-in replacement / bit-for-bit / full toolbox parity
- Simulink-class block diagrams (far future / out of scope near-term)
- General software-eng IDE platform

## Adversarial checklist (architecture)

| Prior risk | Structural mitigation |
|------------|----------------------|
| `float` env | Deleted; `Value`/`Array` protocols |
| `*` vs `.*` | `STAR` + reserved `DOT_*` tokens |
| Matrix syntax as “library” | Reserved AST + tokens in `lang` |
| `;` display | `suppress` on stmts + `DisplayPolicy` |
| Flat dict | `Workspace` frames |
| No plot seam | `PlotSurface` + `GraphicsBackend` |
| No path/functions | `FunctionResolver` + `ToolboxPath` |
| No composition root | `runtime.Session` |

## QA system (five layers, off-the-shelf preferred)

See `docs/QA.md`:

1. Features — `docs/feature_map.yaml` → `openmatlab features`
2. Cases — pytest + `docs/test_catalog.yaml` → `openmatlab cases`
3. Environments — `tests/{unit,conformance,interactive}` (Playwright/Selenium only for future web UI)
4. Tooling — pytest · coverage · gh → `openmatlab test`
5. Defects — **GitHub Issues** canonical → `gh issue` / `openmatlab defects`

Also: `docs/FEATURE_MAP.md`, `docs/TEST_CATALOG.md`, `docs/WORKFLOW.md`.

R&D loop / DoD: `docs/PROCESS.md`. CI: `.github/workflows/ci.yml`.
