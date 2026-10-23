# Acceptance evidence: Epic #997 (V-E4 heatmap and lab figure)

**Epic:** [#997](https://github.com/superche/openmatlab/issues/997)  
**Milestone:** [C-MAPSS PHM vertical (M14)](https://github.com/superche/openmatlab/milestone/14) · [`docs/milestones/M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md)  
**Design:** [`docs/design/EPIC-997-heatmap.md`](../design/EPIC-997-heatmap.md)  
**Captured:** 2026-10-23  
**Functional tip:** `PENDING_FEATURE_SHA` (the feature commit on this branch; re-run the commands there or on a descendant)  
**Rule:** Outputs below come from real local commands. None are invented.

## Verdict

**Ready for user acceptance.** M14 criteria V05 and V06 are **met**. Epic #997 stays **open** until the user accepts it.

`heatmap` draws a matrix or a table. The story calls it for the FD001 sensor correlation. The lab-meeting chart is one `tiledlayout(2, 3)` figure:

- (a) four z-scored unit-1 sensors versus cycle
- (b) early versus late on the V03 channel
- (c) correlation `heatmap` on `[-1 1]`, with a colorbar and `sensor_*` tick labels
- (d) train failure-cycle histogram
- (e) unit 1 train RUL

The layout title is the unit id. The layout xlabel is the footnote: Saxena, Goebel, Simon, and Eklund, PHM08, 2008, and DOI 10.5281/zenodo.15346912 (CC BY 4.0). The raw / `smoothdata` axes is still a second figure, created last, so the V03 and V04 figure checks stay true.

`clustergram`, geographic heatmaps, and brush selection are not in this slice. The colorbar is painted for `heatmap` only. `imagesc` figures are unchanged.

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

$ git check-ignore -v downloads/cmapss/CMAPSSData.zip downloads/cmapss/fd001/train_FD001.txt
.gitignore:10:downloads/	downloads/cmapss/CMAPSSData.zip
.gitignore:10:downloads/	downloads/cmapss/fd001/train_FD001.txt

$ git ls-files downloads/cmapss
(no output)

$ openmatlab features | grep -E 'heatmap|cmapss'
libs.cmapss_fd001                libs       partial  C-MAPSS FD001 runtime download and readtable load
libs.cmapss_metrics              libs       partial  FD001 early/late means, sensor correlation, and train RUL
libs.graphics.heatmap            libs       partial  heatmap for a matrix or a table, with colorbar and tick labels
```

The rendered lab figure is 13.5 by 8 inches. Tick labels use interpreter `none`, so `sensor_14` keeps the underscore. The colorbar runs from -1 to 1. The footnote is two lines and sits under the panels.

## Measurable gate: pytest

```text
$ python3 -m pytest tests/unit/test_heatmap.py tests/bdd/test_heatmap_bdd.py tests/conformance/test_m14_v05_v06.py tests/conformance/test_m14_v04.py tests/conformance/test_m14_v03.py tests/conformance/test_m14_v01_v02.py tests/unit/test_epic774_snapshots.py --tb=line -o addopts= -q --disable-warnings
15 passed, 58 warnings in 37.19s
```

New cases: `tests/unit/test_heatmap.py` (6), `tests/bdd/test_heatmap_bdd.py` (1), `tests/conformance/test_m14_v05_v06.py` (1). The V01/V02, V03, and V04 conformance scripts still pass on the extended story. The M13 snapshot goldens still pass (`tests/unit/test_epic774_snapshots.py`), including the `imagesc` scene, whose colorbar is still not painted.

The full marker, the same command CI runs, after this file existed. `PYTHONPATH=src` is how this machine lets the corpus child import the tree: the editable install sits in the user site, and the runner points `HOME` at a temp directory. CI installs into the interpreter prefix, so that prefix is on the child path without `PYTHONPATH`.

```text
$ PYTHONPATH=src python3 -m pytest -m "unit or bdd" --cov=openmatlab --cov-report=term-missing --cov-fail-under=60 --tb=line -o addopts= -q --disable-warnings
Required test coverage of 60% reached. Total coverage: 77.98%
2251 passed, 1 skipped, 37 deselected, 81 warnings in 163.70s (0:02:43)
```

**Existing tests changed: none.**

## Feature map

`libs.graphics.heatmap` is `partial`: matrix and table entry, `ColorLimits`, a painted colorbar, and readable category ticks for the FD001 story. Cell labels, `ColorMethod` other than `count` and `mean`, `clustergram`, geographic heatmaps, and brush selection are non-goals of this slice.

## Residuals

No new residual. `clustergram`, geographic heatmaps, brush selection, cell labels, and extra `ColorMethod` values are milestone non-goals, not follow-up work. Export of this figure is [#998](https://github.com/superche/openmatlab/issues/998).

## Milestone progress (M14)

- Criteria met: **V05 met**, **V06 met** in [`M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md) (**4 / 10** rows marked met: V03, V04, V05, V06). V01 and V02 were not relabelled in that table; their evidence is [EPIC-994](EPIC-994.md).
- Conformance: V05/V06 passing (`tests/conformance/test_m14_v05_v06.py`). V01/V02, V03, and V04 still passing.
- Remaining gaps (priority order): V01/V02 rows still labelled unmet on the milestone page (evidence in EPIC-994), then V07 [#998](https://github.com/superche/openmatlab/issues/998), V08–V10 [#999](https://github.com/superche/openmatlab/issues/999).

## CI

Required check `test` is the PR check. The URL is added when that run finishes.
