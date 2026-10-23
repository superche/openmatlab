# M16 — BBBC038 nuclei image vertical

GitHub milestone: https://github.com/superche/openmatlab/milestone/16

**Related:**

- [M15 MIT-BIH Arrhythmia vertical](M15-mitbih-vertical.md) (milestone/15): same runtime-download rule and the same acceptance shape (录屏 + 文字 + `.m`). This vertical is a different record and does not reopen MIT-BIH.
- [M14 C-MAPSS PHM vertical](M14-cmapss-vertical.md) (milestone/14, closed): same cache policy. This vertical does not reopen C-MAPSS.
- [M13 Graphics completion](M13-graphics.md) (closed, milestone/13): `tiledlayout` / `nexttile` and baseline `exportgraphics`. Later epics use them for the nuclei figure only.
- [M12 Real-script compatibility gate](M12-corpus-gate.md) (closed, milestone/12): runtime-fetch policy reused here. Corpus burn-down stays a demilestone.
- [Core backlog](https://github.com/superche/openmatlab/milestone/9): left in place. A residual that blocks the story becomes a labelled blocker issue, not an epic of this milestone.
- Data: Broad Bioimage Benchmark Collection BBBC038v1, `stage1_test.zip` only. Landing page https://bbbc.broadinstitute.org/BBBC038. Licence: CC0 1.0.

## Intent

A scientist who already writes MATLAB finishes one pass over a BBBC038 test field of view in the OpenMATLAB Workbench, in their own script style: download the zip, read the image, segment and count nuclei, look at area and shape, and export a multi-panel figure they can take to a group meeting.

The gate is that story. Corpus pass rate, a full Image Processing Toolbox, and an empty Core backlog are outside it.

Approved by Shaw on 2026-10-23 (Defaults, as a block). Milestone title: **BBBC038 nuclei image vertical**. Epics #1020–#1025 are open on milestone/16.

## Exit criteria (measurable)

M16 is **done** only when **all** of V01–V10 hold on `main`. Each criterion has a reproducible `.m`, an exported figure or a numeric assertion, and (from V08) a recording segment that identifies the step.

1. **Story.** Every row below is met. V01–V09 are p0; V10 is p1.
2. **No open `p0` issue** on milestone/16. A labelled blocker that has a workaround does not block close (V10).
3. **Acceptance package.** 录屏 + 文字 + `.m`: a Workbench screen recording, a `docs/acceptance/` write-up, and a story script a third party can rerun from tip `main` and the public Broad zip.
4. **Docs.** Each epic has an accepted `docs/acceptance/EPIC-NNN.md`. CI check `test` on `main` is green.

There is no conformance manifest and no corpus-% threshold on this milestone. Goldens are the pinned zip size and sha256, the FOV sha256, and the `imread` size and class. MathWorks binaries, official outputs, and sample images are never goldens. A mask comparison, if a later epic adds one, is a documented tolerance, not a contest score.

| # | Criterion (scientist result) | Demo | Priority | Epic | Status |
|---|---|---|---|---|---|
| V01 | **Data in hand and clean.** Runtime download of only `stage1_test.zip` from `https://data.broadinstitute.org/bbbc/BBBC038/stage1_test.zip`. Content-Length and file size 9545388 bytes. The zip and the PNGs never appear in the repo or in a PR. Cache dir is gitignored (`downloads/bbbc038/`, same policy as the GPL corpus). | One script run; `git check-ignore` on the cache; `git ls-files` empty | p0 | [#1020](https://github.com/superche/openmatlab/issues/1020) | met |
| V02 | **One FOV in memory.** `imread` loads at least one field of view. Size and class are asserted. The demo file is 8-bit RGBA on disk; `imread` returns uint8 RGB, 256 by 256 by 3. Grayscale is accepted by the same reader and is not required for this FOV. | `.m` + numeric assert | p0 | [#1020](https://github.com/superche/openmatlab/issues/1020) | met |
| V03 | **Binary segmentation.** A reproducible threshold path, default `imbinarize` + `bwareaopen`, with a before/after panel. | Panel, before/after | p0 | [#1021](https://github.com/superche/openmatlab/issues/1021) | met |
| V04 | **Count.** Connected components (`bwlabel` or `bwconncomp`) and `regionprops` (the story subset: Area, Centroid, and Circularity or Eccentricity). The script prints the nucleus count. The count agrees with a mask or a fixed formula inside a documented tolerance. | Numeric table | p0 | [#1022](https://github.com/superche/openmatlab/issues/1022) | unmet |
| V05 | **Morphology summary.** Area histogram and a mean or median area, or circularity. | Panel | p0 | [#1022](https://github.com/superche/openmatlab/issues/1022) | unmet |
| V06 | **Lab-meeting multi-panel figure.** One `tiledlayout`: the FOV, an overlay (`labeloverlay` or `imshow`), the area histogram, and an optional table summary. Footnote cites CC0, Caicedo et al. Nature Methods 2019, and BBBC038v1. | Full figure on screen | p0 | [#1023](https://github.com/superche/openmatlab/issues/1023) | unmet |
| V07 | **Export you can take away.** `exportgraphics` (or `print`) writes PNG **and** PDF. Resolution is enough to project or insert (default ≥ 150 dpi; demo 300 dpi). The crop keeps the title and the footnote. | Non-empty PNG + PDF; visual check | p0 | [#1024](https://github.com/superche/openmatlab/issues/1024) | unmet |
| V08 | **Workbench runs the story.** A real Workbench window runs the story script. The Command Window shows the count and the other key numbers. The Figures panel shows the final figure. | Screen recording (same shape as the M14/M15 acceptance recordings) | p0 | [#1025](https://github.com/superche/openmatlab/issues/1025) | unmet |
| V09 | **Reproducible acceptance package.** Story `.m` and download helper under `demos/bbbc038/`, plus `docs/acceptance/` text (milestone package and per-epic `EPIC-NNN.md`). A third party reproduces from the public Broad zip and tip `main` only. Licence block below, and the statement that the data is not committed. | Package checklist in the acceptance doc | p0 | [#1025](https://github.com/superche/openmatlab/issues/1025) | unmet |
| V10 | **This vertical does not hostage corpus or Core.** Close does not require a corpus-% rise or an empty milestone/9. If a /9 item or an M12/M13 residual blocks the story, file a labelled blocker issue (`vertical-bbbc038` or `m16-blocker`). A workaround means it does not block close. | Issue link, or an explicit "no blocker" note | p1 | [#1025](https://github.com/superche/openmatlab/issues/1025) | unmet |

## Epics

Approved order. Each epic moves the story one step and can be accepted on its own. Epics stay open until Shaw accepts them.

1. **I-E1 [#1020](https://github.com/superche/openmatlab/issues/1020) (p0, M):** runtime download + `imread` — V01, V02. URL and size locked, cache `downloads/bbbc038/` gitignored, one FOV. `stage1_train` and the `imread` option matrix stay out. Evidence: [EPIC-1020](../acceptance/EPIC-1020.md).
2. **I-E2 [#1021](https://github.com/superche/openmatlab/issues/1021) (p0, M):** `imbinarize` / `bwareaopen` — V03. Depends on I-E1. The adaptive-threshold zoo, deep-learning segmentation, and GPU stay out. Evidence: [EPIC-1021](../acceptance/EPIC-1021.md).
3. **I-E3 [#1022](https://github.com/superche/openmatlab/issues/1022) (p0, M):** `bwlabel` / `bwconncomp` + `regionprops` + count and morphology — V04, V05. Depends on I-E2. Contest scoring and a full `regionprops` property matrix stay out.
4. **I-E4 [#1023](https://github.com/superche/openmatlab/issues/1023) (p0, S):** `imshow` / `labeloverlay` + lab-meeting `tiledlayout` — V06. Depends on I-E3. App Designer and brush selection stay out.
5. **I-E5 [#1024](https://github.com/superche/openmatlab/issues/1024) (p0, S):** `exportgraphics` / `print` quality — V07. Depends on I-E4. PNG and PDF at the story's 300 dpi. Third-party `export_fig`, animation, and pixel-identical glyphs stay out.
6. **I-E6 [#1025](https://github.com/superche/openmatlab/issues/1025) (p0, S):** Workbench recording + acceptance package — V08, V09, V10. Depends on I-E1…I-E5. Corpus residuals and the training zip stay out.

**Work order:** #1020, then #1021, then #1022, then #1023, #1024, #1025. V01 and V02 are met by #1020 ([EPIC-1020](../acceptance/EPIC-1020.md)). V03 is met by #1021 ([EPIC-1021](../acceptance/EPIC-1021.md)). V04–V10 are still open.

## Defaults

Approved by Shaw on 2026-10-23, as a block:

1. **Data.** Runtime download only of `https://data.broadinstitute.org/bbbc/BBBC038/stage1_test.zip` (9545388 bytes). Never commit the zip or the PNGs. Cache: `downloads/bbbc038/` (gitignored). The manifest also pins sha256 so a truncated file fails the size check's partner.
2. **Licence and citation.** CC0 1.0. Caicedo et al., Nature Methods 16:1247–1253, 2019, doi:10.1038/s41592-019-0612-7. BBBC038v1, https://bbbc.broadinstitute.org/BBBC038.
3. **Scope.** A few FOVs (default 1, at most 3). Not the training zip. Not a segmentation contest entry.
4. **Goldens.** A mask comparison when the test-set layout supports it, and/or a fixed public formula with a documented tolerance. No MathWorks sample images.
5. **Acceptance.** 录屏 + 文字 + `.m`, the same triad as the M14/M15 evidence packages.
6. **Export.** Gate at least 150 dpi. The demo default is 300 dpi. PNG and PDF.
7. **Blockers.** Milestone/9 and corpus residuals become labelled issues (`vertical-bbbc038` or `m16-blocker`). A workaround does not block M16 close.
8. **Tests.** Existing tests stay as they are. New tests for this vertical are added on their own. Editing an old test needs Shaw's OK first.
9. **Recording.** A real Workbench window, about 2–3 minutes, when I-E6 lands. This epic does not record one.

## Citation

Broad Bioimage Benchmark Collection, BBBC038v1, `stage1_test.zip`. https://bbbc.broadinstitute.org/BBBC038

Licence: CC0 1.0.

- Caicedo, J. C., Goodman, A., Karhohs, K. W., Cimini, B. A., Ackerman, J., Haghighi, M., Heng, C., Becker, T., Doan, M., McQuin, C., Rohban, M., Singh, S., and Carpenter, A. E. (2019). Nucleus segmentation across imaging experiments: the 2018 Data Science Bowl. Nature Methods 16:1247–1253. doi:[10.1038/s41592-019-0612-7](https://doi.org/10.1038/s41592-019-0612-7).

The zip and the PNGs are not in this repository. A script downloads them at runtime into `downloads/bbbc038/`.

## Non-goals

Simulink, Stateflow, App Designer, `uifigure`, and UI controls. A full Image Processing Toolbox. `stage1_train`, a Kaggle contest entry, and deep-learning segmentation. BBBC001 (NC-SA) and MathWorks sample images. Vendoring the zip or the PNGs. Corpus pass rate and milestone/9 as this vertical's main line. Pixel parity with MATLAB. Editing the existing test suite without Shaw's OK.

## Progress snapshot

M16 opened 2026-10-23. **3 / 10** criteria marked met in the table (V01, V02, V03). Epics #1020–#1025 stay open until accepted. I-E1 evidence: [EPIC-1020](../acceptance/EPIC-1020.md). I-E2 evidence: [EPIC-1021](../acceptance/EPIC-1021.md). The milestone timeline is [M16-bbbc038-vertical.md](../acceptance/M16-bbbc038-vertical.md). /9 and corpus residuals do not block close (V10). No `m16-blocker` issue is open.

Next unmet p0 is V04, epic [#1022](https://github.com/superche/openmatlab/issues/1022). This epic does not start it.
