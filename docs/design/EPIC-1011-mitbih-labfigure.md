# Epic #1011 (B-E4): record 100 lab-meeting tiledlayout

Milestone: [M15 MIT-BIH Arrhythmia vertical](../milestones/M15-mitbih-vertical.md), criterion V06.

## Problem

The record-100 story already has the raw excerpt, the filtered trace, the R peaks, the RR series, and the amplitude spectrum, each on its own figure. A lab meeting needs those panels on **one** figure, with titles, axis units, the record id, and the PhysioNet citation.

## Design

- **No new numeric builtin.** `tiledlayout` and `nexttile` are `libs.graphics.layout` (Epic #770). The story reuses `t`, `xshow`, `yshow`, `locs`, `win`, `pks`, `rr`, `freqs`, and `spec`.
- **One 2×2 layout.** `figure` first, then `tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'loose')`. A new layout replaces axes already on that figure, so the figure is created empty.
- **Panels.** (a) raw MLII excerpt. (b) filtered MLII with R-peak markers. (c) RR histogram in **seconds** (`histogram(rr)`, `xlabel('s')`), so the unit set on this figure is s / mV / Hz. (d) `abs(fft)` of the 10 s excerpt, viewed from 0 to 60 Hz. The earlier standalone RR histogram stays in milliseconds.
- **Chrome.** `tl.Title.String` is `MIT-BIH record 100`. The footnote is `tl.XLabel.String`, built with `sprintf` so the three citation lines (Moody & Mark 2001, Goldberger et al. 2000, DOI 10.13026/C2F305) are separate lines. The graphics post-draw already paints a layout title as the figure suptitle and a layout XLabel as figure text.
- **Figure order.** The peak, RR, and spectrum figures are created first. The lab figure comes next. The raw-versus-filtered axes are created last, so the V03 check still sees that panel as `last_figure`. The lab figure's first axes title is the raw panel, so the V04 search on `axes[0]` still finds the earlier single-panel figures.
- **Stdout.** `V06 grid=2 2 tiles=4`, from `tl.GridSize` and `numel(tl.Children)`.

## Non-goals

`exportgraphics` / `print`, PNG, and PDF (B-E5, [#1012](https://github.com/superche/openmatlab/issues/1012), V07). App Designer, brush selection, and an annotation GUI. `spectrogram` as a gate.

## Adversarial review

| Attack | Result |
|---|---|
| New layout wipes the current axes | `figure` is called immediately before `tiledlayout` |
| V03 `last_figure` is no longer the two-line plot | The lab figure is created before the final `figure` / `plot` |
| Lab tile titles steal the V04 `axes[0]` search | Those titles are not `axes[0]`. The raw tile is, and it does not say "R peaks", "RR", or "spectrum" |
| RR units on the lab tile | Seconds, `xlabel('s')`. The standalone histogram remains milliseconds |
| Existing tests | Not modified |
| PhysioNet bytes in the commit | Not done. Cache stays under `downloads/mitbih/` |
