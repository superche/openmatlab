# Epic #998 (V-E5): lab-meeting PNG and PDF

Milestone: [M14 C-MAPSS PHM vertical](../milestones/M14-cmapss-vertical.md), criterion V07. Depends on #997.

## Problem

`exportgraphics` and `print` already write a file (M13 G08). On the FD001 lab figure they threw away the canvas the heatmap renderer had sized (13.5 by 8 inches) and drew into the default figure `Position` (560 by 420 pixels, about 5.8 by 4.4 inches). Rotated `sensor_*` labels piled up, and the colorbar tick labels, and on `print` the layout title, were cut by the page edge.

## Design

`render_to_file` in `libs/figio.py`:

- **Canvas.** A figure with a heatmap keeps the size the renderer just set. Every other figure still exports at `Position` / `ScreenPixelsPerInch`, so a 560-by-420 figure at `-r48` stays 280 by 210 pixels.
- **exportgraphics** crops to the content box plus 0.16 inch of padding. The pad is what keeps the layout title, the colorbar tick labels and the footnote off the cut. An axes export includes that axes' colorbar. Colorbar axes are not counted as panels when the export names one axes.
- **print** keeps the canvas when every artist sits inside it. If a title, label or colorbar tick crosses the edge, the page grows by the same pad. It does not shrink a figure that already fits.
- **Resolution.** `exportgraphics` defaults to 150 dpi. `print -rN` is unchanged, including `-r0` = 96. The story passes `'Resolution', 300`.
- **Story.** `demos/cmapss/story_fd001.m` calls `exportgraphics` on the lab figure twice: `demos/cmapss/out/story_fd001.png` and `story_fd001.pdf`. That directory is gitignored. The zip and the FD001 text stay under `downloads/cmapss/`.

The tiled heatmap canvas leaves `right` at 0.90 (was 0.98) so the colorbar labels have a place inside the page, not only in the crop.

PNG pixels / PDF page inches is the resolution check. A fraction of a pixel of rounding is allowed. The page is the layout canvas (wider than 10.5 inches, taller than 6.5), not the default window.

## Non-goals

Third-party `export_fig`. Animation. Glyphs that match MATLAB pixel for pixel. `ContentType` still selects nothing beyond the format Matplotlib already writes. `Padding` as a name is still accepted and unused; the 0.16 inch pad is the crop, not a new option.

## Adversarial review

| Attack | Result |
|---|---|
| Default `exportgraphics` of the lab figure, no `Resolution` | PNG and PDF, measured dpi within half a pixel of 150 |
| `Resolution` 300, and `print -dpng/-dpdf -r300` | Same figure, measured dpi within half a pixel of 300 |
| Tight crop of title, colorbar labels, footnote | Ink is inset on all four sides; colorbar labels sit to the right of the strip and not on the edge |
| Squashing back to the default window | Page is at least 10.5 by 6.5 inches |
| Plain `print -dpng -r48` of a line plot | Still 280 by 210 (existing Epic #773 test, not edited) |
| C-MAPSS zip or the exported PNG committed | `downloads/cmapss/` and `demos/cmapss/out/` are gitignored |
