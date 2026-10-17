# Epic #770 (M13 G-E3): axes layout

Milestone: [M13 Graphics completion](../milestones/M13-graphics.md), criterion G03. Part of #593 (nice ticks, `yyaxis`).

## Problem

`tiledlayout`, `nexttile` and `yyaxis` were undefined. Auto axis limits were the raw data range (`plot([0.3 9.7])` gave `YLim = [0.3 9.7]`, MATLAB rounds out to `[0 10]`). Every `subplot` reported the full-figure `Position`, and a new `subplot` in a different grid deleted every axes, not only the overlapping ones. `axis equal/square/ij/xy` were accepted but set no property.

## Design

- New module `libs/layout_builtins.py`, registered after the 3-D charts.
- **TiledChartLayout.** `tiledlayout(m,n)`, `tiledlayout('flow'|'vertical'|'horizontal')`, `tiledlayout(fig, ...)` and the `TileSpacing`/`Padding`/`TileIndexing` name-value pairs create a figure child of type `tiledlayout` (class `matlab.graphics.layout.TiledChartLayout`) with `GridSize`, `TileSpacing`, `Padding`, `TileArrangement`, `Title`/`Subtitle`/`XLabel`/`YLabel` text objects. A new layout replaces the figure's axes and layouts. Its tiles are axes that stay figure children in the tree, so every existing axes code path (`gca`, `findobj`, rendering, `delete`) is unchanged; they point at the layout, which reports them as its `Children`, reports itself as their `Parent`, and hides them from the figure's `Children` (MATLAB lists the layout). `ax.Layout` returns `Tile` and `TileSpan`. Deleting the layout deletes its tiles.
- **nexttile.** `nexttile`, `nexttile(k)`, `nexttile(span)`, `nexttile(k, span)`, `nexttile(t, ...)`. Without `k` it takes the first empty tile where the span fits (row-major); `nexttile(k)` on an occupied tile makes that axes current. Flow layouts grow to `ceil(sqrt(n))` columns. No layout: a flow layout is created (documented). Errors: `MATLAB:tiledlayout:NoEmptyTiles`, `...:InvalidTileLocation`, `...:InvalidGridSize`.
- **yyaxis.** `yyaxis left|right` (optionally with an axes) gives the axes two y sides. Children are tagged with the side that was active when they were created; each side keeps its own `YLim`/`YLimMode` and autoscales to its own children; `YLim`, `ylim` and `YAxisLocation` refer to the active side; replace-mode plotting clears only the active side. The renderer draws the right side on a matplotlib twin axes.
- **Nice auto limits.** Auto `XLim`/`YLim` round out to a tick step of 1, 2 or 5 x 10^k with at most 10 intervals (`[0.3 9.7] -> [0 10]`, `1:3 -> [1 3]`, `[1 5] -> [1 5]`); log axes round out to whole decades; `axis tight` still uses the data range. This is our own rule, documented as approximate: MATLAB does not specify its tick picker. `semilogx`/`semilogy`/`loglog` re-autoscale after setting the scale.
- **subplot.** Each `subplot(m,n,p)` (also `p` a vector of cells, and `subplot(mnp)`) gets a `Position` from our own grid rule over the default axes area `[0.13 0.11 0.775 0.815]` (gaps 0.105 x 0.11; documented as approximate, not MATLAB's pixel layout). Only axes whose `Position` overlaps the new one are deleted (documented MATLAB behaviour); the same grid cell is reused. `subplot('Position', pos)` is added.
- **axis modes.** `equal`/`image` set `DataAspectRatio = [1 1 1]` and `DataAspectRatioMode = 'manual'` (`image` also tightens the limits), `square` sets `PlotBoxAspectRatioMode = 'manual'`, `normal` returns both to `'auto'`, `ij`/`xy` set `YDir`. The renderer applies the aspect modes.
- `isgraphics(h, type)` now checks the type.

## Adversarial review

| Attack | Result |
|---|---|
| `tiledlayout(0,2)`, `tiledlayout(2.5,2)`, `tiledlayout(2,2,'TileSpacing','huge')` | MATLAB-style errors |
| `tiledlayout(1,2)` while figure 1 exists | Grid 1x2, not "parent = figure 1" (a leading figure number is a parent only before `m, n` or `'flow'`) |
| `nexttile` past the last tile, `nexttile(5)` on 1x2, `nexttile([1 3])` on 1x2 | `NoEmptyTiles` / `InvalidTileLocation` |
| `yyaxis('up')`, bare `yyaxis` | `MATLAB:yyaxis:InvalidSide` |
| `yyaxis right; plot; yyaxis left; plot; yyaxis right; plot` | Right side replaced only; left plot kept; both limits independent; `saveas` png renders |
| `delete(t)` | Layout and tiles gone; figure has no children |
| `subplot(2,1,1)` after `subplot(2,2,3)` | Both kept (no overlap) |
| `plot([1e-12 2e-12])`, `plot([-Inf 1 NaN 3])`, `plot(5*ones(1,3))`, `semilogy([1 100])` | `[1e-12 2e-12]`, `[1 3]`, `[4 6]`, `[1 100]`; no traceback |
| Existing tests asserting limits (`axis([0 4 0 10])`, `errorbar` `YLim = [1 5]`, `ax.XLim = [0 5]`) | Unchanged, pass |
| Full test suite | Existing tests unchanged; all pass |

## Residuals

- `ax.Layout.Tile = k` (moving a tile by assignment) and `TileIndexing = 'columnmajor'` placement are not implemented; filed as an issue.
- Pixel-accurate subplot/tile geometry is a non-goal (approximate, own rule).
