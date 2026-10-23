# Epic #1024 (I-E5): 300 dpi PNG and PDF of the nuclei lab figure

Milestone: [M16 BBBC038 nuclei image vertical](../milestones/M16-bbbc038-vertical.md), criterion V07.

## Problem

The 2×2 lab figure has a title, four panels, and a one-line citation footnote. `exportgraphics` already crops with a 0.16 inch pad and defaults to 150 dpi. The story needs a PNG and a PDF at 300 dpi that a lab meeting can project, with the title and the footnote still inside the page.

## Design

- **Canvas.** `fig_lab` is already created at `Position` `[100 100 1200 900]` pixels (about 12.5 by 9.4 inches at 96 ppi). `exportgraphics` and `print` export a non-heatmap figure at `Position` / `ScreenPixelsPerInch`. The heatmap canvas path is unchanged.
- **Files.** After the four tiles are drawn, and before `close(fig_lab)`:

  `exportgraphics(fig_lab, png_path, 'Resolution', 300)`

  `exportgraphics(fig_lab, pdf_path, 'Resolution', 300)`

  Paths: `demos/bbbc038/out/story_stage1_test.png` and `story_stage1_test.pdf`. That directory is gitignored. The Broad zip and the FOV PNG stay under `downloads/bbbc038/`.
- **Stdout.** `V07` prints both paths, `dpi=300`, and the two file sizes from `dir`.
- **Check.** PNG pixels / PDF page inches is the resolution. Ink is inset on all four sides. A white band of at least 0.10 inch in the bottom quarter, with ink under it, is the footnote sitting clear of the panels. The title is dark ink in the top 4 percent, above the black FOV. Default `exportgraphics` of the same canvas is 150 dpi. `print -dpng/-dpdf -r300` is the same check.
- **Figure order.** The export uses `fig_lab`. `close(fig_lab)` and `figure(1)` still leave the 1-by-2 panel current and the area histogram as the only other figure.

## Non-goals

Third-party `export_fig`. Animation. Glyphs that match MATLAB pixel for pixel. The Workbench recording (I-E6, [#1025](https://github.com/superche/openmatlab/issues/1025)).

## Adversarial review

| Attack | Result |
|---|---|
| Export after `close` | The file would be the wrong figure. The story exports `fig_lab` first |
| `Resolution` omitted | 150 dpi, still at the 150 dpi floor, title and footnote inset |
| `Resolution` 300 and `print -r300` | Measured dpi within 2% of 300. Page is at least 9 by 7 inches |
| Crop shaves the title or the footnote | Ink inset on every side. A white band of at least 0.10 inch separates the footnote from the panels. The title band is the top 4 percent, above the black FOV |
| V03 / V04 figure tree | `close(fig_lab)` then `figure(1)`. `ntiles` stays 2 |
| Existing graphics tests | Not modified |
| PNG or PDF committed | `demos/bbbc038/out/` is gitignored. The acceptance image is a downscaled review of the export, not the Broad FOV |
