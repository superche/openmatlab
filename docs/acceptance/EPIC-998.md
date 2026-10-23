# Acceptance evidence: Epic #998 (V-E5 export PNG and PDF)

**Epic:** [#998](https://github.com/superche/openmatlab/issues/998)  
**Milestone:** [C-MAPSS PHM vertical (M14)](https://github.com/superche/openmatlab/milestone/14) · [`docs/milestones/M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md)  
**Design:** [`docs/design/EPIC-998-export.md`](../design/EPIC-998-export.md)  
**Captured:** 2026-10-23  
**Functional tip:** `4fbea5f8ca891f93e98d29adf60432a045a136a2` (the feature commit on this branch; re-run the commands there or on a descendant)  
**Rule:** Outputs below come from real local commands. None are invented.

## Verdict

**Ready for user acceptance.** M14 criterion V07 is **met**. Epic #998 stays **open** until the user accepts it.

`demos/cmapss/story_fd001.m` writes the lab-meeting figure twice with `exportgraphics`:

- `demos/cmapss/out/story_fd001.png`
- `demos/cmapss/out/story_fd001.pdf`

The story passes `'Resolution', 300`. `exportgraphics` with no `Resolution` stays at 150 dpi (`tests/unit/test_m14_v07_export.py`). `print -dpng/-dpdf -r300` of the same layout is covered by that test. The page is the heatmap layout canvas (about 12.7 by 8.1 inches after the crop), not the default 560-by-420 window.

The crop leaves a white margin on every side. The layout title (`FD001 unit 1`), the colorbar ticks (`1.00` down to `-1.00`), and the footnote (Saxena PHM08 and DOI 10.5281/zenodo.15346912) are inside the page. Rotated `sensor_*` labels stay readable.

A figure that is not a heatmap still exports at `Position` / `ScreenPixelsPerInch`. The existing Epic #773 check, 560 by 420 pixels at `-r48` is 280 by 210, still passes. That test file was not edited.

`export_fig`, animation, and pixel-identical glyphs are out of this slice. The PNG and PDF under `demos/cmapss/out/` are gitignored. The C-MAPSS zip and text stay under `downloads/cmapss/`.

Citation: A. Saxena, K. Goebel, D. Simon, and N. Eklund, PHM08, 2008. Data: DOI 10.5281/zenodo.15346912 (CC BY 4.0).

## Functional demo (real CLI output)

```text
$ openmatlab -e "run('demos/cmapss/story_fd001.m')"
FD001 train height=20631 width=26 unique_units=100 unit1_cycles=192
V03 dropped sensor_1 sensor_5 sensor_6 sensor_10 sensor_16 sensor_18 sensor_19
V03 unit=1 dropped=7 kept=14 picked=sensor_4 window=15 movmean_agree=0 nlines=3 drop_max=1.36781e-12 keep_min=0.0341246
V04 window=30 sensors=15 same_drop=0
V04 sensor early late delta
V04 sensor_2 642.383 643.383 0.99931
V04 sensor_3 1586.9 1598.81 11.9087
V04 sensor_4 1402.83 1422.96 20.1281
V04 sensor_6 21.6096 21.61 0.000446667
V04 sensor_7 553.948 552.034 -1.91353
V04 sensor_8 2388.06 2388.19 0.130297
V04 sensor_9 9056.06 9087.59 31.5316
V04 sensor_11 47.3561 47.9693 0.613257
V04 sensor_12 521.905 520.278 -1.62719
V04 sensor_13 2388.06 2388.19 0.132977
V04 sensor_14 8137.38 8159.44 22.056
V04 sensor_15 8.41838 8.49808 0.0796948
V04 sensor_17 392.27 395.386 3.116
V04 sensor_20 38.9322 38.5552 -0.377007
V04 sensor_21 23.3592 23.1312 -0.228013
V04 fail_min=128 fail_median=199 fail_max=362 n_units=100 rul0=100 rul_max=361
V04 corr_offmax=0.963157 sensor_14 sensor_9
V04 fft_bin=2 fft_mag=783.392
V05 class=matlab.graphics.chart.HeatmapChart colorbar=on nlabel=15 clim=-1 1
V06 grid=2 3 unit=1 traces=4
V07 png=/workspace/demos/cmapss/out/story_fd001.png pdf=/workspace/demos/cmapss/out/story_fd001.pdf dpi=300

$ python3 -c "from PIL import Image; from pathlib import Path; import re; png=Path('demos/cmapss/out/story_fd001.png'); pdf=Path('demos/cmapss/out/story_fd001.pdf'); im=Image.open(png); raw=pdf.read_bytes(); m=re.search(rb'/MediaBox\\s*\\[\\s*([-0-9.]+)\\s+([-0-9.]+)\\s+([-0-9.]+)\\s+([-0-9.]+)', raw); x0,y0,x1,y1=(float(v) for v in m.groups()); pw,ph=(x1-x0)/72,(y1-y0)/72; w,h=im.size; print(f'png {w}x{h} bytes {png.stat().st_size}'); print(f'pdf bytes {pdf.stat().st_size} page_in {pw:.4f} x {ph:.4f}'); print(f'dpi {w/pw:.3f} {h/ph:.3f}'); print('pdf', raw[:8])"
png 3810x2424 bytes 666789
pdf bytes 48068 page_in 12.7028 x 8.0800
dpi 299.934 300.000
pdf b'%PDF-1.4'

$ git check-ignore -v demos/cmapss/out/story_fd001.png demos/cmapss/out/story_fd001.pdf downloads/cmapss/CMAPSSData.zip downloads/cmapss/fd001/train_FD001.txt
.gitignore:99:demos/cmapss/out/	demos/cmapss/out/story_fd001.png
.gitignore:99:demos/cmapss/out/	demos/cmapss/out/story_fd001.pdf
.gitignore:10:downloads/	downloads/cmapss/CMAPSSData.zip
.gitignore:10:downloads/	downloads/cmapss/fd001/train_FD001.txt

$ git ls-files demos/cmapss/out downloads/cmapss
(no output)

$ openmatlab features | grep -E 'figio|heatmap|cmapss'
libs.cmapss_fd001                libs       partial  C-MAPSS FD001 runtime download and readtable load
libs.cmapss_metrics              libs       partial  FD001 early/late means, sensor correlation, and train RUL
libs.graphics.heatmap            libs       partial  heatmap for a matrix or a table, with colorbar and tick labels
libs.graphics.figio              libs       done     Figure files (own .fig format) and export (savefig, openfig, exportgraphics, print)
```

The PNG is 3810 by 2424 pixels. The PDF page is 12.7028 by 8.0800 inches. Pixels per inch are 299.934 and 300.000, within half a pixel of the requested 300, and above 150. Ink sits 56, 48, 50 and 55 pixels in from the left, top, right and bottom edges, so the crop does not shave the title, the colorbar or the footnote. The default window at 300 dpi would have been about 1750 by 1312 pixels.

## Measurable gate: pytest

The command CI runs. `PYTHONPATH=/workspace/src` is how this machine lets the corpus child import the tree: the editable install sits in the user site, and the runner points `HOME` at a temp directory. CI installs into the interpreter prefix, so that prefix is on the child path without `PYTHONPATH`.

```text
$ PYTHONPATH=/workspace/src python3 -m pytest -m "unit or bdd" --cov=openmatlab --cov-report=term-missing --cov-fail-under=60 --tb=line -o addopts= -q --disable-warnings
Required test coverage of 60% reached. Total coverage: 77.96%
2257 passed, 1 skipped, 37 deselected, 133 warnings in 210.91s (0:03:30)
```

New cases: `tests/unit/test_m14_v07_export.py` (3), `tests/bdd/test_export_story_bdd.py` (1), `tests/conformance/test_m14_v07.py` (1). The V01/V02, V03, V04 and V05/V06 conformance scripts still pass on the extended story. The M13 snapshot goldens still pass, and `tests/unit/test_epic773_figio.py` still passes, including the 280 by 210 print.

**Existing tests changed: none.**

## Feature map

`libs.graphics.figio` stays `done`. The notes now record the layout canvas and the padded crop (Epic #998, V07) on top of the M13 G08 file format. `libs.graphics.heatmap` stays `partial`: the tiled canvas leaves room on the right for colorbar tick labels.

## Residuals

No new residual. Third-party `export_fig`, animation, and pixel-identical glyphs are milestone non-goals, not follow-up work. `ContentType` still does not pick a renderer beyond the file format. `Padding` is still accepted and unused; the 0.16 inch crop pad is fixed. Workbench recording of this export is [#999](https://github.com/superche/openmatlab/issues/999).

## Milestone progress (M14)

- Criteria met: **V07 met** in [`M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md) (**5 / 10** rows marked met: V03, V04, V05, V06, V07). V01 and V02 were not relabelled in that table; their evidence is [EPIC-994](EPIC-994.md).
- Conformance: V07 passing (`tests/conformance/test_m14_v07.py`). V01/V02, V03, V04 and V05/V06 still passing.
- Remaining gaps (priority order): V01/V02 rows still labelled unmet on the milestone page (evidence in EPIC-994), then V08–V10 [#999](https://github.com/superche/openmatlab/issues/999).

## CI

Required check `test` is the PR check. The URL is added when that run finishes.
