# ITER-005 Design: Plot MVP

**Issue:** #5 · **Principles:** AGENTS.md (KISS, low coupling)

## Goal

`plot(x,y)` (and `plot(y)`) from the language → `Session.plots` →
`MatplotlibGraphicsBackend`. Headless-safe via Matplotlib **Agg**.

## Design

| Piece | Choice |
|-------|--------|
| Builtin | `plot(...)` when name not bound in workspace; resolved in `Evaluator` via `IndexExpr` |
| Host | `HostPlotSurface` wraps `GraphicsBackend` |
| Backend | `MatplotlibGraphicsBackend` (Agg); returns figure number as float |
| Session | `create_default` wires graphics when matplotlib importable |
| CI | `matplotlib` in `[dev]` so unit smoke runs without display |

## Non-goals

3-D plots, handles as objects, GUI event loop, Selenium.

## Tests

Unit + Gherkin with `needs_matplotlib`; assert axes has a line, no display required.
