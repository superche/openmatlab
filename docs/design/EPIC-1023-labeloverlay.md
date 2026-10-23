# Epic #1023 (I-E4): lab-meeting tiledlayout overlay figure

Milestone: [M16 BBBC038 nuclei image vertical](../milestones/M16-bbbc038-vertical.md), criterion V06.

## Problem

The story already shows the raw FOV, the opened mask, the nucleus count, and an area histogram on its own figure. A lab meeting needs those on one figure: the original field, a colored overlay, the area histogram with units, a short summary, and a footnote that cites the data.

## Design

- **`labeloverlay(A, L)`.** `A` is 2-D gray or RGB, uint8 or floating. `L` is a 2-D label matrix of the same height and width. Label 0 is copied unchanged. A logical `L` treats true as label 1. Labels must be nonnegative integers.
- **Transparency.** Name `Transparency`, scalar in `[0, 1]`, default 0.5. The label-color weight is `w = 1 - Transparency`. On a labeled pixel, `out = (1 - w) * image + w * color`. `w = 0` copies the image.
- **Colors.** Label `k` (`k >= 1`) uses row `(k - 1) mod 8` of a fixed cycle, stored as RGB/255. These are not the MATLAB `lines` colors: 228 26 28, 55 126 184, 77 175 74, 152 78 163, 255 127 0, 255 255 51, 166 86 40, 247 129 191.
- **Class.** uint8 in, uint8 RGB out, rounded to nearest with ties to even, and only on labeled pixels. A floating image is treated as `[0, 1]` and the result is double RGB; labeled pixels are clipped to `[0, 1]`.
- **Rejected.** A volume, a size mismatch, a negative or non-integer label, `Transparency` outside `[0, 1]`, and any name other than `Transparency` (`Colormap`, `IncludedLabels`).
- **Figure.** `demos/bbbc038/lab_figure.m` builds one 2×2 `tiledlayout` on a new figure. Tiles: `imshow` of the FOV, `imshow` of `labeloverlay(I, L)`, `histogram(areas)` with `Area (px)` and `Count`, and a summary tile (`Nuclei`, mean area, median area) with the axes hidden. The layout title is `BBBC038v1 stage1_test`. The layout `XLabel` is the footnote `CC0 1.0. J. C. Caicedo et al., Nature Methods 16:1247-1253, 2019. BBBC038v1.` The graphics post-draw already paints that title and that footnote.
- **Figure order.** The story runs `lab_figure.m`, prints `V06 grid` and the footnote, then `close(fig_lab)` and `figure(1)`. The current figure stays the 1-by-2 before/after panel. The only other figure stays the histogram titled `BBBC038 areas`. `ntiles` stays 2. The lab grid is `labtiles`. The conformance test runs the story, checks that tree, then runs `lab_figure.m` again and checks the 2×2.
- **Review snapshot.** `docs/acceptance/EPIC-1023-v06.png` is that lab figure saved at 12 by 8 inches and 100 dpi so the footnote is readable. It is not the Broad FOV PNG, and it is not the 300 dpi PNG/PDF gate.

## Non-goals

`Colormap` and `IncludedLabels`. 3-D images. App Designer, brush selection, and an annotation GUI. `exportgraphics` / `print` at 300 dpi (I-E5, [#1024](https://github.com/superche/openmatlab/issues/1024), V07). Committing `stage1_test.zip` or the FOV PNG.

## Adversarial review

| Attack | Result |
|---|---|
| A 2×2 left as `gcf` | V03 requires the current layout to be 1-by-2. The story closes the lab figure and calls `figure(1)` |
| A third alive figure | V04 requires exactly one other figure, the area histogram. `close(fig_lab)` removes the lab figure |
| `ntiles` becomes 4 | `ntiles` stays 2. The lab count is `labtiles` |
| Label 0 re-quantized | Background pixels are copied. Only labeled pixels are rounded |
| Transparency 1 | Weight 0 copies the image, including labeled pixels |
| Label 9 | Same color slot as label 1 |
| `Colormap` | `OpenMATLAB:labeloverlay:BadName` |
| Existing tests | Not modified. V03 and V04 conformance still pass on this story |
| Broad PNG in the commit | Not done. The acceptance PNG is a rendered figure. The cache stays under `downloads/bbbc038/` |
