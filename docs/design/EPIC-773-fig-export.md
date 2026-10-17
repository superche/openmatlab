# Epic #773 (M13 G-E6): figure files and export

Milestone: [M13 Graphics completion](../milestones/M13-graphics.md), criterion G08. Part of #593.

## Problem

`savefig`, `openfig`, `hgsave`, `hgload` and `exportgraphics` were undefined. `print` ignored `-rN` and always saved at Matplotlib's default size. `saveas` rejected `.fig`.

## Decision (Shaw, 2026-10-16)

`.fig` is an **OpenMATLAB-own format** with the same extension. It is **not compatible with MATLAB `.fig` files**: MATLAB cannot open our files, and we reject MATLAB's.

## Design

New module `libs/figio.py`, registered after `gap_leftovers`, so its `print` replaces the earlier one.

- **File format.** A zip archive with `openmatlab-fig.json` (`{"format": "openmatlab-fig", "version": 1}`) and `figure.json`. Each saved figure is a property tree: `Type`, the stored properties, the internal layout attributes (subplot cell, `_rect`, layout tile, yyaxis sides, current axes, legend) and the children in creation order. References between objects (`Title`/`XLabel` text, legend, current axes, layout) are written as `{"$ref": id}`. Referenced objects outside `Children` (labels, legends) are stored as orphans with their parent. NaN and Inf are written as strings (`{"$num": "nan"}`), so the JSON is standard. Numeric, logical and char MATLAB values in properties (`UserData`...) are kept. Structs, cells and objects are written as `[]`, and their property paths are listed in the file's `dropped` field (documented limitation).
- **savefig(h, file)** / `savefig(file)` / `savefig(h)` writes `Untitled.fig`. `h` may be an array of figures. `.fig` is added when the name has no extension, and `'compact'` is accepted. The figure's `FileName` is set. `hgsave` is an alias.
- **openfig(file, 'new'|'reuse', 'visible'|'invisible')** rebuilds the tree with new handles and the next free figure number, and makes the figure current. `'reuse'` returns an open figure that has the same `FileName`. Without a visibility option, the saved `Visible` is kept. `hgload` is an alias. The loaded tree has **zero property difference** from the saved one, apart from handle ids, `Number` and `FileName` (unit test over a scene with subplots, yyaxis, legend, NaN data, manual ticks, ruler format, a normalized text and `UserData`).
- **Rejected files.** A MATLAB `.fig` (a MAT file), any non-zip file or a zip without our header gives `MATLAB:openfig:InvalidFile` ("MATLAB .fig files are not supported"). A file from a newer format version or a damaged tree gives the same identifier, and a partially loaded figure is removed. A missing file gives `MATLAB:openfig:FileNotFound`.
- **exportgraphics(obj, file, ...)** accepts a figure, axes, tiled layout, legend or colorbar and writes `.png`, `.jpg`, `.tif`, `.gif`, `.pdf`, `.eps` or `.svg`, cropped tightly to the content as MATLAB does (an axes crops to that axes). Options: `Resolution` (150 by default), `BackgroundColor` (`'white'` default, `'none'`, `'current'`, RGB), and `ContentType` (validated; Matplotlib chooses vector or raster from the format). `Colorspace` and `Padding` are accepted. `Append` is rejected (`MATLAB:exportgraphics:AppendNotSupported`).
- **print(fig, file, '-dDEVICE', '-rN')** supports the `-dpng`, `-djpeg`, `-dtiff`, `-dpdf`, `-deps`/`-depsc`, `-dsvg` devices, as well as `-rN` (`-r0` = 96, screen), `-fN`, and command syntax. It adds the device's extension when the name has none, and infers the device from the extension otherwise. Printer and clipboard output give `MATLAB:print:NoPrinter`, and `-dbmp`/`-dmeta` give `MATLAB:print:InvalidDevice`. `-painters`/`-opengl`/`-vector`/`-image`/`-loose` are accepted.
- **Size.** Export renders at the figure's size: `Position` in pixels divided by the root `ScreenPixelsPerInch` (96). A 560-by-420 figure at `-r48` gives 280 x 210 pixels. With `InvertHardcopy` `'on'` (the default) the background is white.

## Adversarial review

| Attack | Result |
|---|---|
| A real MATLAB `.fig` (MAT header), random bytes, a zip without our header, a damaged tree | `MATLAB:openfig:InvalidFile`; no partial figure is left open (unit test) |
| NaN in `XData`, yyaxis sides, legend, manual ticks, ruler `TickLabelFormat`, normalized text, matrix `UserData` | Round trip has zero property-tree difference (unit test) |
| Struct `UserData` | Written as `[]`, listed under `dropped` (unit test); never an error |
| `savefig` to a missing folder, `savefig(42, ...)` | `MATLAB:savefig:FileNotWritable`, `MATLAB:savefig:InvalidHandle` |
| `openfig(..., 'reuse')` twice, then `openfig` | One figure, then a second one (unit test) |
| Reopened figure with `hold on` saved | `NextPlot` is restored, so plotting adds (MATLAB); after `hold off` plotting replaces |
| `exportgraphics` bad extension, negative resolution, unknown option; `print -dbmp`; `print(f)` with no file | MATLAB-style identifiers (unit tests) |
| Export size | `-r48` of a 560-by-420 figure is 280 x 210 pixels (unit test) |
| Existing tests | Unchanged; `saveas` still rejects `.fig` (see below) |

## G08 status (blocked, needs Shaw)

Checks s1-s4 (savefig/openfig round trip, `exportgraphics`, `print -dpdf`) pass. Check s5 needs `saveas(g, 'c.fig')` to write a file. The existing Epic #537 unit test `test_saveas_png_and_unsupported_fig` asserts that this call raises "not supported", and changing an existing test needs approval. So `saveas` `.fig` is not enabled and **G08 stays pending** (#979).
