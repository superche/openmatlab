# Epic #772 (M13 G-E5): 2-D chart breadth and annotations

Milestone: [M13 Graphics completion](../milestones/M13-graphics.md), criteria G04 and G07. Ranked first by the corpus `graphics` failures.

## Problem

Only `plot`, `bar` (vector), `scatter` and `histogram` existed. Any other chart function was an undefined function, and setting a documented property that the model did not track (`Units`, `XTick`, `XDir`, `Interpreter`, `BaseValue`...) raised `Unrecognized property`. Together these were the largest T1 failure group of the matlab2tikz suite.

## Design

- New module `libs/chart_builtins.py`, registered after `graphics_builtins`. Every chart is a node of the handle tree with MATLAB's `Type` and full class name: `errorbar` (`ErrorBar`), `area`, `stairs` (`stair`), `stem`, `patch`/`fill` (`patch`), `rectangle`, `line`, `image`/`imagesc` (`image`), `pcolor` (`surface`), `contour`/`contourf` (`Contour`), `quiver`, `colorbar` (`ColorBar`), and `annotation` shapes (`arrowshape`, `textboxshape`, `lineshape`, `doubleendarrowshape`, `textarrowshape`, `rectangleshape`, `ellipseshape`).
- `bar`/`barh` accept matrices (one Bar per column, `grouped`/`stacked`, `Horizontal`). `pie` returns patch+text pairs (2n handles). `hist` returns counts and centres, or draws bars. `loglog`/`semilogx`/`semilogy` are `plot` plus `XScale`/`YScale`. `polar`, `polarplot`, `rose`, `compass` and `spy` draw lines. `plotyy` makes two overlaid axes. `axes(...)`, `zlabel`, `box`, `drawnow`, `caxis`/`clim` are included.
- `text` takes 2-D or 3-D positions, vector positions (one Text per point), cellstr strings and name-value pairs.
- Colormaps: `jet gray hot cool spring summer autumn winter bone copper pink white hsv lines` follow their documented closed-form definitions. `parula` and `turbo` are clean-room approximations (piecewise-linear through a few hand-picked anchors; not MathWorks' tables), per the approved default.
- Documented properties: `KNOWN_PROPS` lists per-type documented properties with their default values. They are accepted by `get`/`set`/dot access and stored without further behaviour, except `XScale`/`YScale`/`XDir`/`YDir`, which the renderer applies. Unknown names still raise `Unrecognized property`. Replace-mode plotting resets the stored axes properties (`XScale`, `YDir`, `CLim`, ticks...), as MATLAB does.
- `set` stores cellstr values (`XTickLabel = {}`), vectors as vectors, and raw MATLAB values (`UserData`). `set(h, 'Parent', ax)` reparents. `scatter(x, y, s, c, 'filled', marker)` is accepted.
- Rendering is best-effort: a chart the matplotlib backend cannot draw is skipped and never fails the script.

## Adversarial review

| Attack | Result |
|---|---|
| `annotation('blob')`, `pie([-1 2])`, `colormap('nosuch')`, `colormap([2 0 0])`, `caxis([3 1])`, `errorbar(1:3)`, `bar(1:3, 1:2)` | MATLAB-style errors, no traceback (unit tests) |
| `set(gca, 'Bogus', 1)` | Still `Unrecognized property` (existing test unchanged) |
| `semilogy(...)` then `plot(...)` | `YScale` back to `linear` |
| `imagesc` then `plot` | `YDir` back to `normal` |
| Rendering every new chart in one figure and `saveas` png | File written |
| `rectangle('Position', ...)` with row vectors, `drawnow` in a loop | No crash (was an internal `TypeError` in the pendulum corpus script) |
| Full test suite | Unchanged existing tests all pass |

Residuals are filed as issues (see the acceptance record): `findobj` (G-E2 #769) blocks the last G07 check; 3-D charts (`surf`, `mesh`, `plot3`, `sphere`, `view`) are G-E4/G06; `xticks`/`yticks`, `imshow`, `title(colorbar, ...)`, and `@ishandle` as a function handle.
