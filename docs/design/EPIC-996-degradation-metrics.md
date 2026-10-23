# Epic #996 (V-E3): FD001 degradation metrics

Milestone: [M14 C-MAPSS PHM vertical](../milestones/M14-cmapss-vertical.md), criterion V04.

## Problem

After the FD001 table is loaded and one unit is smoothed, a script reports three numbers a group meeting can use: how each kept sensor moves from the start of life to the end, how the sensors move together, and when each training unit fails (and the RUL along the way). The values have to match a fixed public formula. `groupsummary` already aggregates a table. `corrcoef` already computes a sample correlation. `heatmap` does not exist yet.

## Design

The formulas live in `demos/cmapss/` and call those builtins. Nothing here fits a PHM model.

- **Failure cycle.** `cmapss_failure_cycles(T)` is `groupsummary(T,'unit','max','cycle')`. `failure_cycle` is the max cycle. `n_cycles` is the row count. Units come back in ascending order.
- **Train RUL.** `cmapss_train_rul(T)` joins that summary back onto `T` and subtracts: `RUL = failure_cycle - cycle`. `join` keeps the left-table row order, including when units are interleaved. The last cycle of each unit is 0. This is the piecewise train label. It is not `RUL_FD001.txt` (that file is one number per test unit) and it is not a learned estimator.
- **Early versus late.** `cmapss_early_late(T, sensors, W)` with `W = 30` in the story. Early rows are `cycle <= W`. Late rows are `cycle > failure_cycle - W`. A unit shorter than `2*W` errors, because the windows would overlap. Each window must contain exactly `W` rows, which is the first `W` and last `W` cycles when the trace is `1..N` with no gaps. The mean is `groupsummary(...,'mean')`, which skips NaNs. FD001 has no missing values, so this is the arithmetic mean. `delta = late_mean - early_mean`. A fleet number is the unweighted mean across units. With exactly `W` rows in every window, that equals the pooled mean.
- **Correlation.** `cmapss_sensor_corr(S)` is `corrcoef(S)`: columns are sensors, the covariance divides by `n-1`, and the diagonal is 1. The story drops sensors whose training-set sample standard deviation is at most `1e-6` (the same idle-channel rule as V03, applied to every train row) before the call, so a constant column does not make the matrix undefined.
- **Story.** `demos/cmapss/story_fd001.m` keeps the V01–V03 lines. It then prints one row per kept sensor (`early`, `late`, `delta` as fleet means), the min / median / max failure cycle, the count of RUL zeros, and the largest off-diagonal correlation. Figure 1 is a 2×2 `tiledlayout`: unit 1 early and late traces of the V03 channel, `imagesc` of the correlation on `[-1 1]` with a colorbar (standing in until `heatmap`), a histogram of failure cycles, and unit 1's RUL. Figure 2 is the existing raw / `smoothdata` axes, created last so it stays the last figure. One `fft` of that unit-1 channel, with the DC bin cleared, is printed as a demo bonus.
- **Goldens.** Unit tests pin the toy early/late/RUL numbers by hand and recompute Pearson as `(X'X)/(n-1)` normalized by the diagonal, without calling the helpers to build the expected matrix. The FD001 conformance test reads `train_FD001.txt` with `numpy.loadtxt` and applies the same formulas. Relative tolerance is `1e-8` with an absolute tolerance of `1e-8` (a near-zero delta must not fail a pure relative check). Failure cycles and RUL are exact. Octave is not required; the formulas are the golden.

Citation, unchanged: A. Saxena, K. Goebel, D. Simon, and N. Eklund, PHM08, 2008; DOI 10.5281/zenodo.15346912.

## Non-goals

A PHM08 contest model, a deep-learning RUL, test-set scoring against `RUL_FD001.txt`, FD002–FD004, and a Predictive Maintenance toolbox. `heatmap` and the lab-meeting footnote are V-E4. The `fft` line is not a gate.

## Adversarial review

| Attack | Result |
|---|---|
| Units interleaved in `T` | RUL follows `T`'s rows. The early/late table is still sorted by unit |
| `W` larger than half the shortest life | `OpenMATLAB:cmapss:Window` before a partial table is returned |
| A gap so a window does not have `W` cycles | Same identifier |
| `W = 2.5` or `W = 0` | Same identifier |
| Constant sensors in the correlation | Dropped with the `1e-6` rule on the full training set. That keeps 15 sensors. Unit 1 still drops seven, including `sensor_6`, which is dust on that unit and not on the fleet |
| Correlation diagonal | 1, and the matrix matches the `n-1` formula within `1e-8` |
| Calling the helpers to build the expected toy means | Not done. The expected early/late/RUL rows are literals |
| FD001 zip | Still only under `downloads/cmapss/`. The story reads through `load_fd001` |
| Existing V03 figure | Created after the metric figure. `last_figure` is still the three-line smoothdata axes |
| Existing tests | Not modified |
