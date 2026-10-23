# M15 — MIT-BIH Arrhythmia vertical

GitHub milestone: https://github.com/superche/openmatlab/milestone/15

**Related:**

- [M14 C-MAPSS PHM vertical](M14-cmapss-vertical.md) (milestone/14, closed): same runtime-download rule and the same acceptance shape (录屏 + 文字 + `.m`). This vertical is a different record and does not reopen C-MAPSS.
- [M13 Graphics completion](M13-graphics.md) (closed, milestone/13): `tiledlayout` / `nexttile` and baseline `exportgraphics`. This vertical uses them for the record-100 figure only.
- [M12 Real-script compatibility gate](M12-corpus-gate.md) (closed, milestone/12): runtime-fetch policy reused here. Corpus burn-down stays a demilestone.
- [Core backlog](https://github.com/superche/openmatlab/milestone/9): left in place. A residual that blocks the story becomes a labelled blocker issue, not an epic of this milestone.
- Data: PhysioNet MIT-BIH Arrhythmia Database, record **100** only, version 1.0.0. DOI [10.13026/C2F305](https://doi.org/10.13026/C2F305). Licence: Open Data Commons Attribution License v1.0 (ODC-By 1.0).

## Intent

A scientist who already writes MATLAB finishes one pass over MIT-BIH record 100 in the OpenMATLAB Workbench, in their own script style: download the three files, read the ECG in millivolts at 360 Hz, bandpass, mark R peaks, look at the RR series and a spectrum, and export a multi-panel figure they can take to a group meeting.

The gate is that story. Corpus pass rate, a full WFDB toolbox, and an empty Core backlog are outside it.

Approved by Shaw on 2026-10-23 (Defaults, as a block). Milestone title: **MIT-BIH Arrhythmia vertical**. Epics #1008–#1013 are open on milestone/15.

## Exit criteria (measurable)

M15 is **done** only when **all** of V01–V10 hold on `main`. Each criterion has a reproducible `.m`, an exported figure or a numeric assertion, and (from V08) a recording segment that identifies the step.

1. **Story.** Every row below is met. V01–V09 are p0; V10 is p1.
2. **No open `p0` issue** on milestone/15. A labelled blocker that has a workaround does not block close (V10).
3. **Acceptance package.** 录屏 + 文字 + `.m`: a Workbench screen recording, a `docs/acceptance/` write-up, and a story script a third party can rerun from tip `main` and the public PhysioNet record.
4. **Docs.** Each epic has an accepted `docs/acceptance/EPIC-NNN.md`. CI check `test` on `main` is green.

There is no conformance manifest and no corpus-% threshold on this milestone. Goldens are a fixed public formula (gain, baseline, checksum) or Octave. MathWorks binaries, official outputs, and screenshots are never goldens. The `.atr` overlay is not a diagnostic golden.

| # | Criterion (scientist result) | Demo | Priority | Epic | Status |
|---|---|---|---|---|---|
| V01 | **Data in hand and clean.** Runtime download of `100.hea`, `100.dat`, and `100.atr` from `https://physionet.org/files/mitdb/1.0.0/`. Sizes 143, 1950000, and 4558 bytes. The three files and the database zip never appear in the repo or in a PR. Cache dir is gitignored (`downloads/mitbih/`, same policy as the GPL corpus). | One script run; `git check-ignore` on the cache; `git ls-files` empty | p0 | [#1008](https://github.com/superche/openmatlab/issues/1008) | met |
| V02 | **ECG in millivolts at 360 Hz.** A clean-room `.hea` + `.dat` reader loads record 100. Two channels (MLII, V5). Header ADC resolution is 11; on-disk format is 212 (12-bit two's complement, two samples in three bytes). `mV = (adc - baseline) / gain` with the header gain and baseline. `Fs = 360`. Sample count matches the header (650000). First sample and the header checksum agree. | `.m` + numeric assert | p0 | [#1008](https://github.com/superche/openmatlab/issues/1008) | met |
| V03 | **Zero-phase bandpass.** On one channel, a bandpass of about 0.5–40 Hz. `filtfilt` is the call (a thin `bandpass` wrapper may sit beside it). Raw and filtered curves share one axes. | Panel (a)/(b), before/after | p0 | [#1009](https://github.com/superche/openmatlab/issues/1009) | met |
| V04 | **R peaks and RR.** `findpeaks` (MinPeakHeight / MinPeakDistance, the story subset) on the filtered ECG. RR series and `histogram`. Peak index within about 1–2 samples, or about 5–10 ms, of an Octave or fixed-formula check on the demo window. `.atr` may be drawn on top; it is not the gate. | Numeric table + RR panel | p0 | [#1010](https://github.com/superche/openmatlab/issues/1010) | met |
| V05 | **Spectrum.** At least one channel's amplitude spectrum via `fft`. `spectrogram` is a demo bonus, not a gate. | Spectrum panel | p0 | [#1010](https://github.com/superche/openmatlab/issues/1010) | met |
| V06 | **Lab-meeting multi-panel figure.** One figure, `tiledlayout` 2×2 (or 2×3): raw excerpt, filtered trace with R peaks, RR histogram, spectrum. Titles, axis labels in s / mV / Hz, record `100`, and a footnote cite DOI 10.13026/C2F305, Moody & Mark 2001, and Goldberger et al. 2000. | Full figure on screen | p0 | [#1011](https://github.com/superche/openmatlab/issues/1011) | met |
| V07 | **Export you can take away.** `exportgraphics` (or `print`) writes PNG **and** PDF. Resolution is enough to project or insert (default ≥ 150 dpi; demo 300 dpi). The crop keeps the title and the footnote. | Non-empty PNG + PDF; visual check | p0 | [#1012](https://github.com/superche/openmatlab/issues/1012) | met |
| V08 | **Workbench runs the story.** A real Workbench window runs the story script. The Command Window shows progress (Fs, peak count, mean RR). The Figures panel shows the final figure. | Screen recording (same shape as the M12/M13 acceptance recordings) | p0 | [#1013](https://github.com/superche/openmatlab/issues/1013) | unmet |
| V09 | **Reproducible acceptance package.** Story `.m` and download helper under `demos/mitbih/`, plus `docs/acceptance/` text (milestone package and per-epic `EPIC-NNN.md`). A third party reproduces from public PhysioNet record 100 and tip `main` only. Licence block below, and the statement that the data is not committed. | Package checklist in the acceptance doc | p0 | [#1013](https://github.com/superche/openmatlab/issues/1013) | unmet |
| V10 | **This vertical does not hostage corpus or Core.** Close does not require a corpus-% rise or an empty milestone/9. If a /9 item or an M12/M13 residual blocks the story, file a labelled blocker issue (`vertical-mitbih` or `m15-blocker`). A workaround means it does not block close. | Issue link, or an explicit "no blocker" note | p1 | [#1013](https://github.com/superche/openmatlab/issues/1013) | unmet |

## Epics

Approved order. Each epic moves the story one step and can be accepted on its own. Epics stay open until Shaw accepts them.

1. **B-E1 [#1008](https://github.com/superche/openmatlab/issues/1008) (p0, M):** runtime download + clean-room WFDB loader for record 100 — V01, V02. URLs and sizes locked, cache `downloads/mitbih/` gitignored, mV at 360 Hz. Other records, the full zip, and a WFDB toolbox stay out. Evidence: [EPIC-1008](../acceptance/EPIC-1008.md).
2. **B-E2 [#1009](https://github.com/superche/openmatlab/issues/1009) (p0, M):** `filtfilt` / `bandpass` (~0.5–40 Hz) — V03. Depends on B-E1. Full `designfilt`, dsp System objects, and GPU stay out. Evidence: [EPIC-1009](../acceptance/EPIC-1009.md).
3. **B-E3 [#1010](https://github.com/superche/openmatlab/issues/1010) (p0, M):** `findpeaks` R detection, RR, `histogram`, `fft` spectrum — V04, V05. Depends on B-E1; may run in parallel with B-E2. An arrhythmia classifier, the 48-record contest, and a required Pan-Tompkins implementation stay out. Evidence: [EPIC-1010](../acceptance/EPIC-1010.md).
4. **B-E4 [#1011](https://github.com/superche/openmatlab/issues/1011) (p0, S):** lab-meeting `tiledlayout` — V06. Depends on B-E3 for the data; layout comes from M13. App Designer and brush selection stay out. Evidence: [EPIC-1011](../acceptance/EPIC-1011.md).
5. **B-E5 [#1012](https://github.com/superche/openmatlab/issues/1012) (p0, S):** `exportgraphics` / `print` quality — V07. Depends on B-E4. PNG and PDF at the story's 300 dpi. Third-party `export_fig`, animation, and pixel-identical glyphs stay out. Evidence: [EPIC-1012](../acceptance/EPIC-1012.md).
6. **B-E6 [#1013](https://github.com/superche/openmatlab/issues/1013) (p0, S):** Workbench recording + acceptance package — V08, V09, V10. Depends on B-E1…B-E5. Corpus residuals and the rest of MIT-BIH stay out.

**Work order:** #1008, then #1009 ∥ #1010, then #1011, #1012, #1013. V01 and V02 are met by #1008 ([EPIC-1008](../acceptance/EPIC-1008.md)). V03 is met by #1009 ([EPIC-1009](../acceptance/EPIC-1009.md)). V04 and V05 are met by #1010 ([EPIC-1010](../acceptance/EPIC-1010.md)). V06 is met by #1011 ([EPIC-1011](../acceptance/EPIC-1011.md)). V07 is met by #1012 ([EPIC-1012](../acceptance/EPIC-1012.md)). V08–V10 are still open.

## Defaults

Approved by Shaw on 2026-10-23, as a block:

1. **Data.** Runtime download only of `https://physionet.org/files/mitdb/1.0.0/100.hea`, `100.dat`, and `100.atr` (143, 1950000, and 4558 bytes). Never commit those files or the full zip. Cache: `downloads/mitbih/` (gitignored). The manifest also pins sha256 so a truncated file fails the size check's partner.
2. **Licence and citation.** ODC-By 1.0. Moody & Mark, PhysioNet, DOI 10.13026/C2F305. Moody & Mark, IEEE Engineering in Medicine and Biology Magazine 20(3):45–50, 2001. Goldberger et al., Circulation 101(23):e215–e220, 2000.
3. **Scope.** Record 100 only. Minimal clean-room `.hea` + `.dat` reader. `.atr` overlay is optional and is not a hard golden.
4. **Goldens.** Header gain, baseline, initial value, and checksum, or an Octave / fixed public formula. Image evidence uses our own renders. The gate is the story plus those numbers.
5. **Acceptance.** 录屏 + 文字 + `.m`, the same triad as the M12/M13/M14 evidence packages.
6. **Blockers.** Milestone/9 and corpus residuals become labelled issues (`vertical-mitbih` or `m15-blocker`). A workaround does not block M15 close.
7. **Tests.** Existing tests stay as they are. New tests for this vertical are added on their own. Editing an old test needs Shaw's OK first.

## Citation

PhysioNet MIT-BIH Arrhythmia Database, record 100, version 1.0.0. https://physionet.org/content/mitdb/1.0.0/

Licence: Open Data Commons Attribution License v1.0 (ODC-By 1.0).

- Moody, G. B., and Mark, R. G. (2001). The impact of the MIT-BIH Arrhythmia Database. IEEE Engineering in Medicine and Biology Magazine, 20(3):45–50.
- Goldberger, A. L., Amaral, L. A. N., Glass, L., Hausdorff, J. M., Ivanov, P. Ch., Mark, R. G., Mietus, J. E., Moody, G. B., Peng, C.-K., and Stanley, H. E. (2000). PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. Circulation 101(23):e215–e220.
- Data DOI: [10.13026/C2F305](https://doi.org/10.13026/C2F305).

The raw files are not in this repository. A script downloads them at runtime into `downloads/mitbih/`.

## Non-goals

Simulink, Stateflow, App Designer, `uifigure`, and UI controls. A full WFDB or Signal Processing toolbox. Any MIT-BIH record other than 100, and the ~73.5 MB database zip. Vendoring PhysioNet bytes. Copying GPL PhysioNet/MATLAB WFDB sources. An arrhythmia classifier, a 48-record contest entry, and a required Pan-Tompkins implementation. Corpus pass rate and milestone/9 as this vertical's main line. Pixel parity with MATLAB. Editing the existing test suite without Shaw's OK.

## Progress snapshot

M15 opened 2026-10-23. **7 / 10** criteria marked met in the table (V01–V07). Epics #1008–#1013 stay open until accepted. B-E1 evidence: [EPIC-1008](../acceptance/EPIC-1008.md). B-E2 evidence: [EPIC-1009](../acceptance/EPIC-1009.md). B-E3 evidence: [EPIC-1010](../acceptance/EPIC-1010.md). B-E4 evidence: [EPIC-1011](../acceptance/EPIC-1011.md). B-E5 evidence: [EPIC-1012](../acceptance/EPIC-1012.md). The milestone timeline is [M15-mitbih-vertical.md](../acceptance/M15-mitbih-vertical.md). /9 and corpus residuals do not block close (V10). No `m15-blocker` issue is open.

Next unmet p0 is V08, epic [#1013](https://github.com/superche/openmatlab/issues/1013).
