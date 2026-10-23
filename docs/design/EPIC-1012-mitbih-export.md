# Epic #1012 (B-E5): record 100 PNG and PDF

Milestone: [M15 MIT-BIH Arrhythmia vertical](../milestones/M15-mitbih-vertical.md), criterion V07.

## Problem

The 2×2 lab figure has a title and a three-line citation footnote. On the default 560-by-420 window those lines sit on top of the bottom tiles. `exportgraphics` already crops with a 0.16 inch pad (M14, Epic #998) and defaults to 150 dpi. The story needs a PNG and a PDF at 300 dpi that a lab meeting can project, with the title and the footnote still readable.

## Design

- **Canvas.** `fig_lab` is created at `Position` `[100 100 1200 900]` pixels (about 12.5 by 9.4 inches at 96 ppi). Fonts stay in points, so the extra inches open a gap under the tiles for the footnote and between the panel titles. `exportgraphics` and `print` already export a non-heatmap figure at `Position` / `ScreenPixelsPerInch`. The heatmap canvas path is unchanged.
- **Files.** After the four tiles are drawn, and before the raw-versus-filtered axes (those stay the last figure):

  `exportgraphics(fig_lab, png_path, 'Resolution', 300)`

  `exportgraphics(fig_lab, pdf_path, 'Resolution', 300)`

  Paths: `demos/mitbih/out/story_record100.png` and `story_record100.pdf`. That directory is gitignored. PhysioNet bytes stay under `downloads/mitbih/`.
- **Stdout.** `V07` prints both paths, `dpi=300`, and the two file sizes from `dir`.
- **Check.** PNG pixels / PDF page inches is the resolution. A white band of at least 0.10 inch in the bottom quarter, with ink under it, is the footnote sitting clear of the panels. Ink is inset on all four sides. Default `exportgraphics` of the same canvas is 150 dpi. `print -dpng/-dpdf -r300` is the same check.

## Non-goals

Third-party `export_fig`. Animation. Glyphs that match MATLAB pixel for pixel. The Workbench recording (B-E6, [#1013](https://github.com/superche/openmatlab/issues/1013)).

## Adversarial review

| Attack | Result |
|---|---|
| Default 560-by-420 window | The footnote overlaps the bottom tiles. The story does not use that size |
| `Resolution` omitted | 150 dpi, still above the 150 dpi floor, title and footnote inset |
| `Resolution` 300 and `print -r300` | Measured dpi within 2% of 300. Page is at least 9 by 7 inches, not the default window |
| Crop shaves the title or the footnote | Ink inset on every side. A white band of at least 0.10 inch separates the footnote from the panels |
| V03 `last_figure` | The export uses `fig_lab`. The two-line axes are created after it |
| Existing graphics tests | Not modified. A plain `print -dpng -r48` is still 280 by 210 |
| PNG or PDF committed | `demos/mitbih/out/` is gitignored |
