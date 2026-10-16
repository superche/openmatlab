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
| G01 | Handle arrays `h(k).Prop` read/write; `[h.Prop]`, `get(h,'Prop')` cell; `class(h)` full `matlab.graphics.*` name; "Line with properties" display; `isgraphics`/`isvalid`/`delete` on arrays; `double(h)` compatible | m13_g01_handle_arrays | p0 | #768 (#673) | pending |
| G02 | `findobj` (Type/value/`-depth`/`-regexp`/`-and`/`-or`/`-not`), `findall`, `allchild`, `gco`, `ancestor`, `axes(...)`, `groot`; MATLAB Children order | m13_g02_findobj | p0 | #769 (#593) | pending |
| G03 | `subplot` replace/position, `tiledlayout`/`nexttile`, `yyaxis`, nice-tick auto limits, `axis equal/tight/square/ij/xy/off` | m13_g03_layout_axes | p0 | #770 (#593) | pending |
| G04 | `errorbar`, `area`, `stairs`, `stem`, `pie`, `barh`/stacked/grouped `bar`, `histogram` properties, `fill`/`patch`, `line` | m13_g04_charts2d | p1 | #772 (#593) | pending |
| G05 | `colormap` tables (parula approx./jet/gray/hot…), `colorbar`, `caxis`/`clim`, `image`/`imagesc`/`imshow` basics | m13_g05_colour_image | p0 | #771 (#593) | pending |
| G06 | `plot3`, `scatter3`, `surf`/`mesh`/`surfc`, `contour`/`contourf`, `bar3`, `view`, `zlabel`/`zlim`, `shading`, `light`/`lighting` (approx.) | m13_g06_3d | p1 | #771 (#593) | pending |
| G07 | `text` (3-D position, Interpreter), `annotation` (line/arrow/textbox/rectangle), `legend` (Location/`'off'`/DisplayName) | m13_g07_annotation | p1 | #772 | pending |
| G08 | `savefig`/`openfig` round-trip with zero property-tree diff (own `.fig` format); `exportgraphics`; `print -dpng/-dpdf -rN`; `saveas` `.fig` | m13_g08_save_export | p0 | #773 (#593) | pending |
| G09 | Workbench: script/function `fprintf`/`disp`/warning/error output goes to the Command Window (#760); figures dock in the Figures panel; new figure takes focus | m13_g09_workbench_figures | p0 | #767, #774 (#760) | pending |
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

G-E1..G-E7 are ranked after M12 C-E4 using corpus `graphics` failure counts. Absorbed residuals are referenced, not moved: #593 (all), #673 (graphics part only; datetime part stays), #760.

## Non-goals

MATLAB `.fig` binary compatibility; `uifigure`/App Designer/UI controls; interactive tools; animation (`getframe`/`VideoWriter`); pixel parity with MATLAB; toolbox graphics (community plugins).

## Progress snapshot

M13 opened 2026-10-16. **0 / 10** criteria met.
