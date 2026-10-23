# M14 — C-MAPSS PHM vertical

GitHub milestone: https://github.com/superche/openmatlab/milestone/14

**Related:**

- [M13 Graphics completion](M13-graphics.md) (closed, milestone/13): `tiledlayout` / `nexttile` and baseline `exportgraphics` (G08). This vertical polishes the FD001 story figure only.
- [M12 Real-script compatibility gate](M12-corpus-gate.md) (closed, milestone/12): runtime-fetch policy reused here. Corpus burn-down stays a demilestone.
- [M10 Tables and data types](M10-tables.md) (closed): `readtable` and grouping. Only the headerless, space-delimited edges the story needs are in scope; the rest of #721 stays on #721.
- [Core backlog](https://github.com/superche/openmatlab/milestone/9): left in place. A residual that blocks the story becomes a labelled blocker issue, not an epic of this milestone.
- Data: NASA C-MAPSS on Zenodo, record [15346912](https://zenodo.org/records/15346912), DOI [10.5281/zenodo.15346912](https://doi.org/10.5281/zenodo.15346912), CC BY 4.0. Cite Saxena PHM08 with that DOI.

## Intent

A PHM scientist or analyst who already writes MATLAB finishes one week of FD001 work in the OpenMATLAB Workbench, in their own script style: download, read the table, preprocess, degradation metrics, a multi-panel figure, and an export they can take to a group meeting or a paper draft.

The gate is that story. Corpus pass rate, toolbox parity, and an empty Core backlog are outside it.

Approved by Shaw on 2026-10-23 (Defaults, as a block). Milestone title: **C-MAPSS PHM vertical**. Epics #994–#999 are open on milestone/14.

## Exit criteria (measurable)

M14 is **done** only when **all** of V01–V10 hold on `main`. Each criterion has a reproducible `.m`, an exported figure or a numeric assertion, and a recording segment that identifies the step.

1. **Story.** Every row below is met. V01–V09 are p0; V10 is p1.
2. **No open `p0` issue** on milestone/14. A labelled blocker that has a workaround does not block close (V10).
3. **Acceptance package.** 录屏 + 文字 + `.m`: a Workbench screen recording, a `docs/acceptance/` write-up, and a story script a third party can rerun from tip `main` and the public Zenodo record.
4. **Docs.** Each epic has an accepted `docs/acceptance/EPIC-NNN.md`. CI check `test` on `main` is green.

There is no conformance manifest and no corpus-% threshold on this milestone. Goldens are Octave or a fixed public formula. MathWorks binaries, official outputs, and screenshots are never goldens.

| # | Criterion (scientist result) | Demo | Priority | Epic | Status |
|---|---|---|---|---|---|
| V01 | **Data in hand and clean.** Runtime download of `CMAPSSData.zip` (about 12.4 MB) from Zenodo, unzip to `train_FD001.txt`, `test_FD001.txt`, and `RUL_FD001.txt`. The zip and the raw text never appear in the repo or in a PR. Cache dir is gitignored (`downloads/`, same policy as the GPL corpus). | One script run; `git status` clean; `git check-ignore` on the cache | p0 | [#994](https://github.com/superche/openmatlab/issues/994) | unmet |
| V02 | **Read the table the usual way.** Headerless space-delimited `train_FD001.txt` loads with `readtable` (or a documented `readmatrix` path) into a table. 26 columns use PHM08 names (unit, cycle, 3 settings, 21 sensors). `height` and a chosen unit's row count match the published FD001 scale (fixed assert, not a MathWorks binary). | `.m` + numeric assert | p0 | [#994](https://github.com/superche/openmatlab/issues/994) | unmet |
| V03 | **Preprocess as written.** On a chosen unit, drop near-constant sensors and smooth. `smoothdata` is the primary call (`movmean` / `gaussian` and a window at minimum); `movmean` may sit beside it. Raw and smoothed curves share one axes. | Panel (a), before/after or dual line | p0 | [#995](https://github.com/superche/openmatlab/issues/995) | unmet |
| V04 | **Reportable metrics.** At least: early-vs-late cycle sensor-mean difference, a sensor correlation matrix, and per-unit failure cycle or RUL (train RUL = max(cycle) − cycle). Values match Octave or a fixed public formula within a relative tolerance (about 1e-8 to 1e-6, set by magnitude). Optional single-channel `fft` is a demo bonus, not a gate. | Numeric table + panels (b) and (d) | p0 | [#996](https://github.com/superche/openmatlab/issues/996) | unmet |
| V05 | **Correlation heatmap.** `heatmap` shows the sensor correlation with a readable colorbar and tick labels. `imagesc` plus manual ticks may stand in for #996 only; V05 is met when the story calls `heatmap`. | Panel (c) | p0 | [#997](https://github.com/superche/openmatlab/issues/997) | unmet |
| V06 | **Lab-meeting multi-panel figure.** One figure, `tiledlayout` 2×2 (or 2×3): sensor vs cycle, early/late overlay, correlation heatmap, failure-cycle or RUL distribution. Titles, axis labels, unit id, and a footnote cite Saxena PHM08 and Zenodo DOI 10.5281/zenodo.15346912. | Full figure on screen | p0 | [#997](https://github.com/superche/openmatlab/issues/997) | unmet |
| V07 | **Export you can take away.** `exportgraphics` (or `print`) writes PNG **and** PDF. Resolution is enough to project or insert (default ≥ 150 dpi; demo 300 dpi). The crop keeps the title and the colorbar. The files drop into slides. | Non-empty PNG + PDF; visual check | p0 | [#998](https://github.com/superche/openmatlab/issues/998) | unmet |
| V08 | **Workbench runs the story.** A real Workbench window runs the story script. The Command Window shows progress and the key numbers. The Figures panel shows the final figure. | Screen recording (same shape as the M12/M13 acceptance recordings) | p0 | [#999](https://github.com/superche/openmatlab/issues/999) | unmet |
| V09 | **Reproducible acceptance package.** Story `.m` and download helper under `demos/`, plus `docs/acceptance/` text (milestone package and per-epic `EPIC-NNN.md`). A third party reproduces from public Zenodo and tip `main` only. Licence block: CC BY 4.0, Saxena PHM08, Zenodo DOI, and the statement that the data is not committed. | Package checklist in the acceptance doc | p0 | [#999](https://github.com/superche/openmatlab/issues/999) | unmet |
| V10 | **This vertical does not hostage corpus or Core.** Close does not require a corpus-% rise or an empty milestone/9. If a /9 item or an M12/M13 residual blocks the story, file a labelled blocker issue (`vertical-cmapss` or `m14-blocker`). A workaround means it does not block close. | Issue link, or an explicit "no blocker" note | p1 | [#999](https://github.com/superche/openmatlab/issues/999) | unmet |

## Epics

Approved order. Each epic moves the story one step and can be accepted on its own.

1. **V-E1 [#994](https://github.com/superche/openmatlab/issues/994) (p0, S):** runtime download + FD001 `readtable` loader — V01, V02. Zenodo URL locked, sha256/size manifest, cache `downloads/cmapss/` gitignored, PHM08 column names. FD002–FD004 and full `detectImportOptions` stay out.
2. **V-E2 [#995](https://github.com/superche/openmatlab/issues/995) (p0, M):** `smoothdata` (`movmean` / `gaussian` + window) and near-constant channel drop — V03. Depends on V-E1. Full method matrix, GPU, and timetable resampling stay out. Minimal `fillmissing` / `rmmissing` only if the story script needs them (FD001 is normally complete).
3. **V-E3 [#996](https://github.com/superche/openmatlab/issues/996) (p0, M):** degradation metrics + Octave/formula goldens — V04. Depends on V-E1; may run in parallel with V-E2. Contest models, deep-learning RUL, and a Prognostics toolbox stay out. `imagesc` may stand in until V-E4.
4. **V-E4 [#997](https://github.com/superche/openmatlab/issues/997) (p0, M):** `heatmap` + lab-meeting `tiledlayout` — V05, V06. Depends on V-E3 for the data; layout comes from M13. `clustergram`, geo heatmaps, and brush selection stay out.
5. **V-E5 [#998](https://github.com/superche/openmatlab/issues/998) (p0, M):** `exportgraphics` / `print` quality for the multi-panel figure — V07. Depends on V-E4. PNG and PDF are the story default. Third-party `export_fig`, animation, and pixel-identical glyphs stay out.
6. **V-E6 [#999](https://github.com/superche/openmatlab/issues/999) (p0, S):** Workbench recording + acceptance package — V08, V09, V10. Depends on V-E1…V-E5. Corpus residuals and MIT-BIH stay out.

**Work order:** #994, then #995 ∥ #996, then #997, #998, #999. The highest unmet p0 in table order is V01, so V-E1 is first.

## Defaults

Approved by Shaw on 2026-10-23, as a block:

1. **Data.** Runtime download of `https://zenodo.org/records/15346912/files/CMAPSSData.zip?download=1`. Check size and sha256 in a manifest. Never commit the zip or the extracted text (same policy as GPL/GFDL corpus sources). Cite Saxena PHM08 and Zenodo DOI 10.5281/zenodo.15346912. Licence: CC BY 4.0.
2. **Scope.** FD001 only. FD002–FD004 may appear as a demo bonus; they are not exit criteria.
3. **Goldens.** Octave or a fixed public formula, with a numeric tolerance. Image evidence uses our own renders (M13 snapshot tooling may be reused). The gate is the story plus the metrics.
4. **Acceptance.** 录屏 + 文字 + `.m` (Workbench recording, write-up, reproducible script), the same triad as the M12/M13 evidence packages.
5. **Blockers.** Milestone/9 and M12/M13 demilestone residuals become labelled issues. A workaround does not block M14 close. `normalize(...,'zscore')` covers a missing `zscore`. `movmean` may stand in for `smoothdata` until V-E2.
6. **Backup datasets.** MIT-BIH is not on the path. CWRU is not vendored.
7. **Tests.** Existing tests stay as they are. New demo or conformance asserts for this vertical are added on their own. Editing an old test needs Shaw's OK first.

## Non-goals

Simulink, Stateflow, App Designer, `uifigure`, and UI controls. Full Signal Processing, Predictive Maintenance, or Prognostics toolbox parity. Corpus pass rate and the M12 burn-down as this vertical's main line. MIT-BIH as required work; vendoring CWRU; File Exchange, NCM, or MathWorks sample data. Pixel parity with MATLAB; MATLAB `.fig` binary compatibility (M13's own format stands). A full `smoothdata` / `heatmap` / `fillmissing` method matrix beyond the story. FD002–FD004, a full PHM08 contest model, and deep-learning RUL. `pspectrum` (`fft` covers a demo). `datetime` (cycles are the time base; M10 T09 already exists). Editing the existing test suite without Shaw's OK.

## Progress snapshot

M14 opened 2026-10-23. **0 / 10** criteria met. Epics #994–#999 are open on milestone/14. Next unmet p0 is V01 (#994). /9 and corpus residuals do not block close.
