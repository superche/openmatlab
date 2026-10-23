# Acceptance evidence: Epic #996 (V-E3 degradation metrics)

**Epic:** [#996](https://github.com/superche/openmatlab/issues/996)  
**Milestone:** [C-MAPSS PHM vertical (M14)](https://github.com/superche/openmatlab/milestone/14) · [`docs/milestones/M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md)  
**Design:** [`docs/design/EPIC-996-degradation-metrics.md`](../design/EPIC-996-degradation-metrics.md)  
**Captured:** 2026-10-23  
**Functional tip:** `14204a1c7be9ae2968d6f2103d0f664717e7c79f` (the feature commit on this branch; re-run the commands there or on a descendant)  
**Rule:** Outputs below come from real local commands. None are invented.

## Verdict

**Accepted.** Shaw accepted Epic #996 on 2026-10-23 (Asia/Shanghai); M14 criterion V04 is **met**. Milestone/14 is closed.

Train FD001 metrics are the public formulas, computed with `groupsummary` and `corrcoef`:

- Failure cycle of a unit is `max(cycle)`. Train RUL is `failure_cycle - cycle`, so the last cycle of each unit is 0. `join` keeps the table's row order.
- Early and late means use the first and last 30 cycles (`cycle <= 30` and `cycle > failure_cycle - 30`). Each unit is weighted once. `delta` is late minus early.
- Sensor correlation is the sample Pearson matrix (`corrcoef`, covariance divided by `n-1`). Sensors whose training-set sample standard deviation is at most `1e-6` are dropped first.

The story prints a 15-row fleet table, draws early/late traces, an `imagesc` of the correlation (standing in until `heatmap`), a failure-cycle histogram, and unit 1's RUL. One `fft` of unit 1's `sensor_4` is printed as a demo bonus. It is not part of the V04 gate.

Octave is not installed on the machine that captured this evidence (`command -v octave` produced no path). The golden is the formula, evaluated in the tests on the text file with `numpy.loadtxt`, not by calling the helpers. Relative tolerance is `1e-8`, with an absolute floor of `1e-8` so a near-zero delta still has a bound. Failure cycles and RUL are exact.

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

$ git check-ignore -v downloads/cmapss/CMAPSSData.zip downloads/cmapss/fd001/train_FD001.txt
.gitignore:10:downloads/	downloads/cmapss/CMAPSSData.zip
.gitignore:10:downloads/	downloads/cmapss/fd001/train_FD001.txt

$ git ls-files downloads/cmapss
(no output)
```

Unit 1 still drops seven idle sensors. The fleet metric table keeps 15: `sensor_6` is dust on unit 1 (`same_drop=0`) and moves across the fleet, so the `1e-6` rule keeps it. Failure cycles run from 128 to 362 (median 199). Every unit has one RUL of 0 (`rul0=100`), and the longest train RUL is 361, which is `362 - 1`. The strongest off-diagonal correlation is `sensor_14` with `sensor_9` (0.963). The fft bonus peaks in bin 2.

Agreement with the formula on this tip. `train_FD001.txt` was read with `numpy.loadtxt` and passed through `reference()` in `tests/conformance/test_m14_v04.py`; the story workspace was compared with the scaled residual `max(|engine-formula| / max(|formula|, 1e-8))`:

```text
fail_exact True
rul_exact True
rel_early 6.576359255496319e-16
rel_late 6.382220401841964e-16
rel_delta 2.965743592705324e-11
rel_fleet_delta 2.1475698629223167e-12
rel_corr 5.8767504377339385e-15
```

All of those sit inside `1e-8`.

## Measurable gate: pytest

```text
$ python3 -m pytest tests/unit/test_cmapss_metrics.py tests/bdd/test_cmapss_metrics_bdd.py tests/conformance/test_m14_v04.py tests/conformance/test_m14_v03.py tests/conformance/test_m14_v01_v02.py --tb=line -o addopts= -q --disable-warnings
6 passed in 11.11s

$ python3 -m pytest -m "unit or bdd" --tb=line -o addopts= -q --disable-warnings
2241 passed, 1 skipped, 37 deselected, 29 warnings in 107.11s (0:01:47)
```

New cases: `tests/unit/test_cmapss_metrics.py` (2), `tests/bdd/test_cmapss_metrics_bdd.py` (1), `tests/conformance/test_m14_v04.py` (1). The V01/V02 and V03 conformance scripts still pass on the extended story. The toy in the unit test interleaves two units, so a join that reordered rows would fail the RUL literal `[3, 2, 1, 0, 3, 2, 1, 0]`.

**Existing tests changed: none.**

## Feature map

```text
$ openmatlab features | grep -E 'smoothdata|cmapss'
libs.cmapss_fd001                libs       partial  C-MAPSS FD001 runtime download and readtable load
libs.smoothdata                  libs       partial  smoothdata movmean and gaussian with an explicit window
libs.cmapss_metrics              libs       partial  FD001 early/late means, sensor correlation, and train RUL
```

`libs.cmapss_metrics` is `partial`: FD001 train metrics at a fixed window of 30 cycles. Contest models, learned RUL, and test-set scoring are non-goals of this slice.

## Residuals

No new residual. A PHM08 contest model, deep-learning RUL, scoring `RUL_FD001.txt`, and FD002–FD004 are milestone non-goals, not follow-up work. `heatmap` and the lab-meeting layout are [#997](https://github.com/superche/openmatlab/issues/997). The `imagesc` panel is the temporary correlation view this epic is allowed to ship.

## Milestone progress (M14)

- Criteria met: **V04 met** in [`M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md) (2 / 10 rows marked met: V03, V04). V01 and V02 were not relabelled in that table; their evidence is [EPIC-994](EPIC-994.md).
- Conformance: V04 passing (`tests/conformance/test_m14_v04.py`). V01/V02 and V03 still passing. V05–V10 have no scripts yet (epics #997–#999).
- Remaining gaps at capture (priority order): V01/V02 rows were still labelled unmet on the milestone page (evidence in EPIC-994), then V05–V06 [#997](https://github.com/superche/openmatlab/issues/997), V07 [#998](https://github.com/superche/openmatlab/issues/998), V08–V10 [#999](https://github.com/superche/openmatlab/issues/999).
- Close-out (2026-10-23, Asia/Shanghai): Shaw accepted this epic. Milestone/14 is closed at **10 / 10**. V01 and V02 are **met** in the milestone table.

## CI

Required check `test` is the PR check. The URL is added when that run finishes.
