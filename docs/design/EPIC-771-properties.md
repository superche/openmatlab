# Epic #771 (M13 G-E4) follow-up: remaining axes, ruler, figure and text properties

Milestone: [M13 Graphics completion](../milestones/M13-graphics.md). Part of #593. Follows the colour/3-D delivery ([design](EPIC-771-colour-3d.md)); G05 still waits for Shaw on #866, G06 is met.

## Problem

Probing the documented properties showed the gaps that remained after G-E1..G-E5: `XTick`/`YTick` were empty in auto mode and setting `ax.XTick` left `XTickMode` at `'auto'`; `XTickLabel` was empty until set; `ax.XAxis` was a placeholder `[]`, so `ax.XAxis.TickLabelFormat = ...` and `ax.YAxis(2).Color` failed; changing `Units` never converted `Position`; `ax.FontSize` did not reach the title and labels; `xtickangle` was undefined; `InnerPosition`, `TickLabelInterpreter`, `GridColor`/`GridAlpha`, `Legend`, `MarkerIndices`, `CloseRequestFcn`, callbacks and others were unrecognized; and the renderer ignored manual ticks, label rotation, `TickDir`, `Box`, fonts and the `Interpreter` of text. The corpus has no remaining `graphics-property` failures of this kind (its `graphics property` rows are misclassified function-handle errors), so the scope comes from the MATLAB property documentation, as G01 did.

## Design

New module `libs/axes_props.py`, registered after `layout_builtins` (it wraps `_get_prop`/`_set_prop`, `known`, `EXTRA_DRAW` and `POST_DRAW`, as the earlier graphics modules do).

- **Ticks.** Auto `XTick`/`YTick`/`ZTick` come from the current limits with the 1/2/5 x 10^k rule of the nice auto limits (#770): at most 10 intervals, whole decades on log axes. This is our own rule and is documented as approximate, because MATLAB does not specify its tick picker. Auto labels are `sprintf(TickLabelFormat, tick/10^Exponent)` (`'%g'`); log axes use `10^{k}`. Setting a tick or label property sets its mode to `'manual'`. Setting a mode to `'manual'` freezes the current values, and setting it to `'auto'` recomputes them. Numeric and char-matrix `XTickLabel` values become one label per element or row. `xtickangle`/`ytickangle`/`ztickangle` set `*TickLabelRotation` and its mode.
- **Rulers.** `ax.XAxis`/`YAxis`/`ZAxis` (and the hidden `XRuler`...) return `matlab.graphics.axis.decorator.NumericRuler` objects (type `numericruler`), owned by the axes but not listed in `Children`, so `findobj` does not return them. These ruler properties proxy the axes properties: `Limits`, `LimitsMode`, `TickValues`, `TickValuesMode`, `TickLabels`, `TickLabelsMode`, `Direction`, `Scale`, `Color`, `TickLabelRotation`, `MinorTick`, `Label`, `TickDirection`, `TickLength`, `FontSize`, `FontName`, `FontWeight`, `LineWidth` and `TickLabelInterpreter`. `Exponent` (an integer; setting it makes `ExponentMode` manual), `TickLabelFormat` and `Visible` belong to the ruler itself. With `yyaxis`, `YAxis` is a 2-by-1 array (left; right). The inactive side's `Limits` read and write that side's stored limits. Each side has its own `Color`, which defaults to the first and second `ColorOrder` colour.
- **Units.** Setting `Units` on a figure, axes, legend, colorbar or tiled layout converts `Position` and `OuterPosition`, as MATLAB does. Pixel positions are 1-based: normalized 0 is pixel 1, so the default axes reads `[73.8 47.2 434 342.3]` in a 560-by-420 figure. Physical units use the root `ScreenPixelsPerInch` (96). `characters` are approximated as 5 x 13.125 pixels. A figure converts against the root `ScreenSize`; axes and legends convert against their figure. Text converts between `data`, `normalized` and the physical units relative to the axes box, and accounts for log scale and `XDir`/`YDir` reverse. `text(x, y, s, 'Units', u)` takes `x, y` in `u` (MATLAB), not in data units. Setting an axes `Position` updates the rendered rectangle. `InnerPosition` is the axes `Position`. A figure's `InnerPosition`/`OuterPosition` read its `Position`, because a headless figure has no window frame (documented approximation).
- **Fonts.** The title and labels follow the axes `FontSize` times `TitleFontSizeMultiplier`/`LabelFontSizeMultiplier` (1.1) until their own `FontSize` is set. Titles are bold by default.
- **New documented properties.** Axes: `TickLabelInterpreter`, `GridColor`, `GridAlpha`, `MinorGrid*`, `Legend` (the legend handle or empty), `InnerPosition`, `FontAngle`, `*TickLabelRotationMode` and others. Figure: `CloseRequestFcn` (`'closereq'`), `SizeChangedFcn`, `Window*Fcn`, `KeyPressFcn`, `GraphicsSmoothing`, `DockControls`, `WindowState`. Line: `MarkerIndices` (`1:n`), `SeriesIndex`, `*DataSource`. Text: `LineWidth`, `LineStyle`, `Editing`, `FontUnits`. All objects: `ButtonDownFcn`, `CreateFcn`, `DeleteFcn`, `ContextMenu`. Enumerated values (`TickDir`, `Interpreter`, `TickLabelInterpreter`, `XDir`, `XScale`, `Units`) are validated with MATLAB identifiers.
- **Rendering** is best-effort, applied after the existing passes: manual ticks and labels, label rotation, `TickDir`, `Box`, axes `Color`, `XColor`/`YColor` and ruler colour, grid colour, `LineWidth`, `XAxisLocation`/`YAxisLocation`, font sizes and weights, text `FontSize`/`Rotation`/alignment/`BackgroundColor`/`Units`. `tex` strings are translated to Matplotlib mathtext: `^`/`_` with braces or one character, Greek letters and common symbols, and `\bf`/`\it`/`\rm`/`\color`/`\fontsize` dropped as style only. `latex` strings are passed through, and `none` strings are drawn literally. Any string that Matplotlib's mathtext parser rejects is drawn literally, so a malformed label never raises.

## Adversarial review

| Attack | Result |
|---|---|
| `ax.XTick = [3 1]`, `ax.TickDir = 'sideways'`, `ax.XAxis.Exponent = 1.5`, `ax.Units = 'furlongs'`, `ax.XAxis.Bogus = 1`, `t.Interpreter = 'html'`, `ax.Position = [0 0 1]`, `xtickangle('a')` | MATLAB-style errors with identifiers (unit tests) |
| Malformed TeX/LaTeX (`x^{`, `$\frac{1$`, unknown `\nope`, stray `$`) in titles, labels, tick labels and text, then `saveas` png | Drawn literally; no exception (unit test renders it) |
| `ax.XTickMode = 'manual'` then `xlim([0 20])` | Ticks stay frozen; back to `'auto'` recomputes `0:2:20` |
| Round trip `Units` pixels -> normalized | Returns the original `Position` (to rounding; unit test) |
| `text(0.25, 0.75, 'u', 'Units', 'normalized')` | Position stays `[0.25 0.75 0]` (not converted from data); converting to `data` gives `[3.25 7.75 0]` on `XLim = YLim = [1 10]` |
| Ruler under `yyaxis`: set the inactive side's `Limits` | Applies to that side only; reading `ylim` after switching shows it |
| Label with its own `FontSize`, then the axes `FontSize` changes | The label keeps its own size; the other labels follow the multiplier |
| `findobj(ax)` after reading `ax.XAxis` | Rulers are not `Children`, so they are not returned |
| Existing tests | Unchanged; the full unit, bdd and conformance suites pass |

## Residuals

- `XTickLabel`/`TickLabels` are returned as a 1-by-N cell. MATLAB returns N-by-1. An existing Epic #772 unit test indexes the result as `(1,2)`, so changing the shape needs Shaw's approval (#977).
- The tick picker, the 1-based pixel convention for text (none), `characters` units and the figure frame are documented approximations. The tick label exponent is applied only when `Exponent` is set (MATLAB also picks it automatically for large values).
