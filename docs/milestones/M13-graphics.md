# M13 — Graphics completion

GitHub milestone: https://github.com/superche/openmatlab/milestone/13

**Related:**
- [M12 Real-script compatibility gate](M12-corpus-gate.md) runs interleaved; its `graphics` failure counts rank G-E3..G-E6.
- [M11 Debugger and Workbench](M11-debugger-workbench.md) (closed): Workbench model and #760.
- [`../GAP-ANALYSIS.md`](../GAP-ANALYSIS.md) (Graphics rows).

## Intent

Make basic MATLAB graphics (plot functions, the handle object model, figure save/load/export) good enough that common scripts run and can query and modify properties correctly, with correct Workbench output and figure routing. Today only 2-D basics exist (about 30 builtins) and handles are plain numeric ids.

Approved by Shaw on 2026-10-16. Decisions:
1. **`.fig`** uses an **OpenMATLAB-own format** (zipped JSON property tree) with the same extension, documented as **incompatible with MATLAB `.fig`**.
2. **`class(h)`** returns the full MATLAB class name (e.g. `matlab.graphics.chart.primitive.Line`); `double(h)` stays numeric-compatible.
3. **parula** is a clean-room approximation with documented differences; jet/hot/gray are formula-based.
4. **3-D (G06) and annotations (G07) stay in M13.**
5. **#760** is fixed right away as G-E0.

## Exit criteria (measurable)

M13 is **done** only when **all** of these hold on `main`:

1. **Conformance.** Every criterion in [`tests/conformance/m13_manifest.py`](../../tests/conformance/m13_manifest.py) is `met`, and `pytest tests/conformance/test_m13_conformance.py` reports **0 xfail**.
2. **No open `p0` issue** on milestone/13.
3. **No Python traceback** in a probe sweep over the graphics builtins.
4. **Docs.** No doc drift; CI on `main` is green; each epic has an accepted `docs/acceptance/EPIC-NNN.md`.

Primary gate: handle-model property assertions from MATLAB documentation. Secondary gate (G10): image snapshots compared against our own reviewed renders (never MathWorks screenshots); ≤ 1 % pixels with ΔE > 10 or SSIM ≥ 0.98.

## Criteria

| # | Criterion | Script | Priority | Epic | Status |
|---|-----------|--------|----------|------|--------|
| G01 | Handle arrays `h(k).Prop` read/write; `[h.Prop]`, `get(h,'Prop')` cell; `class(h)` full `matlab.graphics.*` name; "Line with properties" display; `isgraphics`/`isvalid`/`delete` on arrays; `double(h)` compatible | m13_g01_handle_arrays | p0 | #768 (#673) | **met** (Epic #768, [design](../design/EPIC-768-handle-model.md)) |
| G02 | `findobj` (Type/value/`-depth`/`-regexp`/`-and`/`-or`/`-not`), `findall`, `allchild`, `gco`, `ancestor`, `axes(...)`, `groot`; MATLAB Children order | m13_g02_findobj | p0 | #769 (#593) | **met** (Epic #769, [design](../design/EPIC-769-object-queries.md)) |
| G03 | `subplot` replace/position, `tiledlayout`/`nexttile`, `yyaxis`, nice-tick auto limits, `axis equal/tight/square/ij/xy/off` | m13_g03_layout_axes | p0 | #770 (#593) | **met** (Epic #770, [design](../design/EPIC-770-layout.md)) |
| G04 | `errorbar`, `area`, `stairs`, `stem`, `pie`, `barh`/stacked/grouped `bar`, `histogram` properties, `fill`/`patch`, `line` | m13_g04_charts2d | p1 | #772 (#593) | **met** (Epic #772, [design](../design/EPIC-772-charts2d.md)) |
| G05 | `colormap` tables (parula approx./jet/gray/hot…), `colorbar`, `caxis`/`clim`, `image`/`imagesc`/`imshow` basics | m13_g05_colour_image | p0 | #771 (#593) | pending (5/6 checks pass; the 256-colour default needs an approved change to an Epic #772 unit test, see [design](../design/EPIC-771-colour-3d.md)) |
| G06 | `plot3`, `scatter3`, `surf`/`mesh`/`surfc`, `contour`/`contourf`, `bar3`, `view`, `zlabel`/`zlim`, `shading`, `light`/`lighting` (approx.) | m13_g06_3d | p1 | #771 (#593) | **met** (Epic #771, [design](../design/EPIC-771-colour-3d.md)) |
| G07 | `text` (3-D position, Interpreter), `annotation` (line/arrow/textbox/rectangle), `legend` (Location/`'off'`/DisplayName) | m13_g07_annotation | p1 | #772 | **met** (Epics #772 and #769, [design](../design/EPIC-772-charts2d.md)) |
| G08 | `savefig`/`openfig` round-trip with zero property-tree diff (own `.fig` format); `exportgraphics`; `print -dpng/-dpdf -rN`; `saveas` `.fig` | m13_g08_save_export | p0 | #773 (#593) | pending |
| G09 | Workbench: script/function `fprintf`/`disp`/warning/error output goes to the Command Window (#760); figures dock in the Figures panel; new figure takes focus | m13_g09_workbench_figures | p0 | #767, #774 (#760) | pending (output routing delivered by Epic #767; docking/focus wait for #774) |
| G10 | ≥ 40 golden snapshot scenes within tolerance; deterministic rendering | m13_g10_snapshots | p1 | #774 | pending |

## Epics

1. **G-E0 #767 (p0):** Workbench output routing — G09 first half; #760. **First epic overall.**
2. **G-E1 #768 (p0):** handle model upgrade — G01; graphics part of #673.
3. **G-E2 #769 (p0):** object queries — G02.
4. **G-E3 #770 (p0):** layout — G03.
5. **G-E4 #771 (p0):** colour/image + 3-D — G05, G06.
6. **G-E5 #772 (p1):** 2-D charts + annotations — G04, G07.
7. **G-E6 #773 (p0):** `.fig` + export — G08.
8. **G-E7 #774 (p1):** figure docking + snapshot infrastructure — G09 second half, G10.

G-E1..G-E7 are ranked after M12 C-E4 using corpus `graphics` failure counts. **Ranked 2026-10-16** (see [Corpus ranking](#corpus-ranking)). Absorbed residuals are referenced, not moved: #593 (all), #673 (graphics part only; datetime part stays), #760.


## Corpus ranking

Source: the first full M12 corpus run ([`REPORT.md`](../corpus/REPORT.md)). There are 37 `graphics` failures. Each is mapped to the epic whose criterion covers the failing function.

| Rank | Epic | Corpus `graphics` failures | Functions (count) | Criterion priority |
|---|---|---|---|---|
| 1 | G-E5 #772 | 18 | errorbar 3, patch 3, fill 2, stem 2, loglog, stairs, line, area, rectangle, polarplot, spy, hist | p1 (G04, G07) |
| 2 | G-E4 #771 | 11 | sphere 3, imagesc 3, plot3, pcolor, contourf, colormap, imshow | p0 (G05), p1 (G06) |
| 3 | G-E2 #769 | 4 | axes(...) 3, findobj | p0 (G02) |
| 4 | G-E1 #768 | 2 | handle property access 2 | p0 (G01) |
| 4 | G-E3 #770 | 2 | plotyy 2 (-> yyaxis) | p0 (G03) |
| 6 | G-E6 #773 | 0 | none | p0 (G08) |
| 6 | G-E7 #774 | 0 | none | p1 (G09 second half, G10) |

**Work order** (the highest-priority unmet criterion first, then corpus count; G-E1 stays ahead of G-E2..G-E6 because they build on its handle model): G-E1 #768 -> G-E4 #771 -> G-E2 #769 -> G-E3 #770 -> G-E6 #773 -> G-E5 #772 -> G-E7 #774. The M12 p0 burn-down C-E6 #766 (C05, C06, C09) is interleaved ahead of the p1 epics.

## Non-goals

MATLAB `.fig` binary compatibility; `uifigure`/App Designer/UI controls; interactive tools; animation (`getframe`/`VideoWriter`); pixel parity with MATLAB; toolbox graphics (community plugins).

## Progress snapshot

M13 opened 2026-10-16. **6 / 10** criteria met: G01 (Epic #768), G02 (Epic #769), G04 and G07 (Epic #772), G06 (Epic #771), G03 (Epic #770, [design](../design/EPIC-770-layout.md): `tiledlayout`/`nexttile`, `yyaxis`, `subplot` geometry with overlap replace, nice auto limits, `axis` modes). G-E0 #767 delivered the G09 output-routing half (#760; [design](../design/EPIC-767-output-routing.md)); G09 flips when G-E7 #774 adds figure docking. G05 is 5/6: the 256-colour default needs Shaw's decision on an existing Epic #772 unit test (#866). Pending: G05 (#866), G08 (G-E6 #773), G09 and G10 (G-E7 #774). Next: G-E6 #773, G-E7 #774, interleaved with M12 C-E5 #765.
