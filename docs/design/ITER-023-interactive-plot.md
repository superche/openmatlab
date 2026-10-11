# Design: interactive plot / show policy (Issue #23)

**Epic:** #19 · **KISS**

## Decision
- Default backend remains **Agg** (`interactive=False`) for CI / headless.
- Enable interactive when `OPENMATLAB_PLOT_INTERACTIVE=1` (or `true`/`yes`) **and** not in CI (`CI` / `GITHUB_ACTIONS` unset/false).
- `Session.create_default(interactive_plots: Optional[bool]=None)` resolves via env+CI.
- Language builtin **`show`** (and alias **`drawnow`**) → `PlotSurface.show()` → Matplotlib `plt.show()` only if interactive; Agg no-op (still returns).
- `HostPlotSurface.show()` / `GraphicsBackend.show()` already on backend; surface gains `show`.

## Non-goals
GUI toolkit selection, figure handles as objects, `pause`, live tweak widgets.
