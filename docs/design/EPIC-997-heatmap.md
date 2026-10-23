# Epic #997 (V-E4): heatmap and the lab-meeting figure

Milestone: [M14 C-MAPSS PHM vertical](../milestones/M14-cmapss-vertical.md), criteria V05 and V06.

## Problem

The FD001 story already has a sensor correlation matrix. V-E3 drew it with `imagesc` and manual ticks. A script a PHM group would actually write calls `heatmap`, and the figure they take to the meeting is one `tiledlayout`: sensor traces, early versus late, the heatmap, and the failure-cycle / RUL panels, with the unit id and a citation on the figure.

`tiledlayout`, `nexttile`, `title`, `xlabel`, and the colorbar object already exist. The colorbar object is not painted (the M13 `imagesc` goldens have no colorbar strip). This slice paints a colorbar for `heatmap` only.

## Design

`libs/heatmap_builtins.py` registers `heatmap`. The chart is an axes child of type `heatmap` (`matlab.graphics.chart.HeatmapChart`). Colour is an `image` on that same axes, so `nexttile` then `heatmap(...)` stays in the tile, and `title` / `xlabel` / `ylabel` keep addressing `gca`.

- **Matrix.** `heatmap(C)` labels both axes `1..n`. `heatmap(x, y, C)` uses `x` for the columns and `y` for the rows, in the order given. `C` must be `length(y)` by `length(x)`. `x` and `y` are a cell array of text or a numeric vector (`%g`).
- **Table.** `heatmap(T, xvar, yvar)` counts rows in each pair. `heatmap(T, xvar, yvar, 'ColorVariable', cvar)` is the mean of `cvar` (non-finite values dropped; an empty pair is NaN and drawn in `MissingDataColor`). Text categories keep first-seen order. Numeric categories sort by value. `ColorMethod` is `'count'` or `'mean'` only.
- **Scale.** `ColorLimits` is a rising pair, stored on the chart and used as the image norm. The default is the finite range of the data, or `[0 1]` when that range is empty. The default colormap is the existing parula approximation, passed only to this image. `ColorbarVisible` `'on'` (the default) or `'off'`.
- **Labels.** Tick labels are manual. `TickLabelInterpreter` is `'none'`, so `sensor_14` stays `sensor_14`. Eight or more columns rotate the x labels 90 degrees and the figure pads the x label down past them. `XDisplayLabels` / `YDisplayLabels` replace the labels and must have one entry per category.
- **Colorbar.** After the axes ticks are applied, the render adds a matplotlib colorbar on that axes only. `imagesc` figures are unchanged, so the M13 snapshot goldens stay put.
- **Room.** A figure that contains a heatmap is drawn at 13.5 by 8 inches when it also has a tiled layout (6.4 by 5.2 otherwise), with wider gaps. Other figures keep the default size.
- **Footnote.** `TiledChartLayout` already stores `Title` and `XLabel`. Those strings are drawn as the figure title and a bottom footnote when they are non-empty. A textbox annotation is drawn the same way. Empty titles are skipped, so a bare `tiledlayout` snapshot does not grow a title.
- **Story.** `demos/cmapss/story_fd001.m` keeps the V01–V04 numbers. The first figure is `tiledlayout(2, 3)`: (a) four z-scored unit-1 sensors versus cycle, (b) early versus late on the V03 channel, (c) `heatmap` of the correlation on `[-1 1]` down the right column, (d) the failure-cycle histogram, (e) unit 1 train RUL. The layout title is the unit id. The layout xlabel cites Saxena PHM08 and DOI 10.5281/zenodo.15346912. The raw / `smoothdata` axes is still created after that figure, so it stays the last figure.

Citation, unchanged: A. Saxena, K. Goebel, D. Simon, and N. Eklund, PHM08, 2008; DOI 10.5281/zenodo.15346912.

## Non-goals

`clustergram`, geographic heatmaps, and brush or other interactive selection. Cell labels, `ColorMethod` other than `count` and `mean`, and a full property matrix. Export polish is V-E5. The `fft` line is still not a gate.

## Adversarial review

| Attack | Result |
|---|---|
| `heatmap(x, y, C)` with the wrong shape | `OpenMATLAB:heatmap:SizeMismatch` before a chart is returned |
| A 3-D array, or no arguments | `OpenMATLAB:heatmap:ColorData` / `MATLAB:narginchk:notEnoughInputs` |
| `ColorLimits` that do not rise | `OpenMATLAB:heatmap:ColorLimits` |
| `ColorMethod` `'median'`, or `'mean'` on a bare matrix | Named errors, no chart |
| Unknown name-value | `MATLAB:class:InvalidProperty` |
| Table pair that never occurs | Mean cell is NaN, drawn with the missing colour; the count cell is 0 |
| Repeated table pair | Mean is the arithmetic mean of the finite values, not the last row |
| `sensor_14` under the default tex interpreter | Ticks use `'none'`, so the underscore is not a subscript |
| `heatmap` inside `nexttile` | One figure. The image is on that tile. The colorbar is an extra matplotlib axes, not a second figure |
| Painting every colorbar | Not done. M13 `imagesc` goldens still match |
| Existing V03 / V04 figure contract | The smoothdata axes is still last and still has three lines. The metric axes titles the V04 test searches for are still on the first figure, and the heatmap image array is `C` |
| FD001 zip | Still only under `downloads/cmapss/` |
| Existing tests | Not modified |
