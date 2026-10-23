# Acceptance evidence: Epic #995 (V-E2 smoothdata and near-constant drop)

**Epic:** [#995](https://github.com/superche/openmatlab/issues/995)  
**Milestone:** [C-MAPSS PHM vertical (M14)](https://github.com/superche/openmatlab/milestone/14) · [`docs/milestones/M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md)  
**Design:** [`docs/design/EPIC-995-smoothdata.md`](../design/EPIC-995-smoothdata.md)  
**Captured:** 2026-10-23  
**Functional tip:** `FUNCTIONAL_TIP` (the feature commit on this branch; re-run the commands there or on a descendant)  
**Rule:** Outputs below come from real local commands. None are invented.

## Verdict

**Ready for user acceptance.** M14 criterion V03 is **met**. Epic #995 stays **open** until the user accepts it.

`smoothdata` accepts `movmean` and `gaussian` with an explicit window. `movmean` calls the existing builtin (default flag `omitnan`). `gaussian` uses `sigma = window/5` for a scalar window and rescales weights on the truncated window. `demos/cmapss/story_fd001.m` drops unit 1's near-constant sensors and plots the raw series with both smoothers on one axes.

`fillmissing` and `rmmissing` are not implemented. The FD001 story does not call them.

Citation: A. Saxena, K. Goebel, D. Simon, and N. Eklund, PHM08, 2008. Data: DOI 10.5281/zenodo.15346912 (CC BY 4.0).

## Functional demo (real CLI output)

```text
$ openmatlab -e "a = smoothdata(1:6, 'movmean', 4); b = movmean(1:6, 4); d = max(abs(a-b)); g = smoothdata([0 0 0 10 0 0 0], 'gaussian', 3); fprintf('movmean_row=%g %g %g %g %g %g diff=%g spike=%g\n', a(1), a(2), a(3), a(4), a(5), a(6), d, g(4));"
movmean_row=1.5 2 2.5 3.5 4.5 5 diff=0 spike=6.67243

$ openmatlab -e "run('demos/cmapss/story_fd001.m')"
FD001 train height=20631 width=26 unique_units=100 unit1_cycles=192
V03 dropped sensor_1 sensor_5 sensor_6 sensor_10 sensor_16 sensor_18 sensor_19
V03 unit=1 dropped=7 kept=14 picked=sensor_4 window=15 movmean_agree=0 nlines=3 drop_max=1.36781e-12 keep_min=0.0341246

$ git check-ignore -v downloads/cmapss/CMAPSSData.zip downloads/cmapss/fd001/train_FD001.txt
.gitignore:10:downloads/	downloads/cmapss/CMAPSSData.zip
.gitignore:10:downloads/	downloads/cmapss/fd001/train_FD001.txt

$ git ls-files downloads/cmapss
(no output)
```

Unit 1 drops the seven idle sensors (`sensor_1`, `sensor_5`, `sensor_6`, `sensor_10`, `sensor_16`, `sensor_18`, `sensor_19`). Their sample std is numerical dust (`drop_max` about `1e-12`, under the story threshold `1e-6`). The quietest kept sensor has std about `0.034`. The plotted channel is `sensor_4`. `smoothdata(...,'movmean',15)` matches `movmean` exactly (`movmean_agree=0`). The axes has three lines (raw, movmean, gaussian).

## Measurable gate: pytest

```text
$ python3 -m pytest tests/unit/test_smoothdata.py tests/bdd/test_smoothdata_bdd.py tests/conformance/test_m14_v03.py tests/conformance/test_m14_v01_v02.py --tb=no -o addopts= -q --disable-warnings
9 passed in 1.73s

$ python3 -m pytest -m "unit or bdd" --tb=no -o addopts= -q --disable-warnings
2237 passed, 1 skipped, 37 deselected, 29 warnings in 97.91s (0:01:37)
```

New cases: `tests/unit/test_smoothdata.py` (5), `tests/bdd/test_smoothdata_bdd.py` (2), `tests/conformance/test_m14_v03.py` (1). The V01/V02 conformance script still passes on the extended story.

**Existing tests changed: none.**

## Feature map

```text
$ openmatlab features | grep -E 'smoothdata|cmapss'
libs.cmapss_fd001                libs       partial  C-MAPSS FD001 runtime download and readtable load
libs.smoothdata                  libs       partial  smoothdata movmean and gaussian with an explicit window
```

`libs.smoothdata` is `partial`: movmean and gaussian with an explicit window. The rest of the method list, automatic windows, tables, and timetables are non-goals of this slice.

## Residuals

No new residual. The methods outside this slice (`movmedian`, lowess, loess, rlowess, rloess, sgolay), automatic windows, `SmoothingFactor`, tables, timetables, duration windows, and GPU are milestone non-goals (full method matrix), not follow-up work. `fillmissing` / `rmmissing` stay out because the story does not call them. FD002–FD004 stay out. Heatmap and the lab-meeting layout are [#997](https://github.com/superche/openmatlab/issues/997).

## Milestone progress (M14)

- Criteria met: **V03 met** in [`M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md) (1 / 10 rows marked met). V01 and V02 were not relabelled in that table; their evidence is [EPIC-994](EPIC-994.md).
- Conformance: V03 passing (`tests/conformance/test_m14_v03.py`). V01/V02 still passing. V04–V10 have no scripts yet (epics #996–#999).
- Remaining gaps (priority order): V01/V02 rows still labelled unmet on the milestone page (evidence in EPIC-994), then V04 [#996](https://github.com/superche/openmatlab/issues/996), V05–V06 [#997](https://github.com/superche/openmatlab/issues/997), V07 [#998](https://github.com/superche/openmatlab/issues/998), V08–V10 [#999](https://github.com/superche/openmatlab/issues/999).

## CI

Required check `test` is the PR check. The URL is added when that run finishes.
