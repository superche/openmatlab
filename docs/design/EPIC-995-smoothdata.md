# Epic #995 (V-E2): smoothdata and near-constant sensors

Milestone: [M14 C-MAPSS PHM vertical](../milestones/M14-cmapss-vertical.md), criterion V03.

## Problem

On one FD001 unit a script drops sensors that never move, then smooths a remaining channel and plots the raw series on the same axes. The call it writes is `smoothdata(x,'movmean',15)` or `smoothdata(x,'gaussian',15)`. `movmean` already exists. `smoothdata` did not. FD001 has no missing entries, so `fillmissing` / `rmmissing` stay out.

## Design

`libs/smoothdata.py` registers `smoothdata` next to the other numeric builtins.

- **Arguments.** `smoothdata(A, method, window)`, or with a dimension before the method. `window` is a positive scalar or `[b f]`, validated by the same helper as `movmean`. `'omitnan'` / `'includenan'` (and the `*missing` aliases) and `'SamplePoints', t` are accepted. The default missing-value flag is `'omitnan'`, which is the documented `smoothdata` default and is not the `movmean` default.
- **movmean.** The method calls the existing `movmean` builtin with that window, dimension, flag, and sample points. Where the series has no NaNs, `smoothdata(A,'movmean',window)` and `movmean(A,window)` are the same values. Where it has NaNs, the cross-check is `movmean(...,'omitnan')`.
- **gaussian.** Same window membership as `movmean`: a scalar `k` is the half-open interval `[t-k/2, t+k/2)`, and `[b f]` is the closed interval `[t-b, t+f]`. Endpoints truncate, they do not pad. The Gaussian standard deviation is one fifth of the window width: `sigma = k/5` for a scalar, and `sigma = (b+f+1)/5` for `[b f]`. That ratio is the public staff description of `smoothdata` (MATLAB Central answers 406563 and 471173), not a fit to a MathWorks binary. Weights are `exp(-1/2 (d/sigma)^2)`, with `d` in samples or in sample-point units, and each window is rescaled so the weights that remain sum to 1. A NaN is dropped under `'omitnan'` and poisons the window under `'includenan'`.
- **Second output.** `[B, winsize] = smoothdata(...)` echoes the window that was passed.
- **Window required.** Omitting `window`, and passing `SmoothingFactor`, raises `OpenMATLAB:smoothdata:WindowRequired` / `UnsupportedOption`. The reference says an automatic window attenuates about `100*τ` percent of the energy and does not publish the estimator.
- **Story.** `demos/cmapss/story_fd001.m` keeps the V01/V02 print, then takes unit 1, drops sensor columns whose sample std is at most `1e-6`, smooths the kept channel with the largest std (`movmean` and `gaussian`, window 15), and plots raw and both smoothers with one `plot` call. `movmean(raw, 15)` is computed beside `smoothdata` so the script can print the max absolute difference.

Citation for the series, unchanged from V-E1: A. Saxena, K. Goebel, D. Simon, and N. Eklund, PHM08, 2008; DOI 10.5281/zenodo.15346912.

## Non-goals

The rest of the method list (`movmedian`, lowess, loess, rlowess, rloess, sgolay). Automatic windows and `SmoothingFactor`. Tables, timetables, `DataVariables`, `ReplaceValues`. Duration windows. GPU. `fillmissing` / `rmmissing` (the FD001 story does not call them). A full tiled layout is V-E4; this story draws the before/after lines on one axes.

## Adversarial review

| Attack | Result |
|---|---|
| `smoothdata(1:6,'movmean',4)` versus `movmean(1:6,4)` | Identical, including the even-window endpoint values `[1.5 2 2.5 3.5 4.5 5]` |
| NaNs with the default flag | Matches `movmean(...,'omitnan')`, not bare `movmean` |
| `'lowess'`, `'sgolay'`, a table, `SmoothingFactor`, a missing window | Named errors, no partial result |
| Window `0` | `MATLAB:smoothdata:invalidWindow` from the shared window check |
| Gaussian on a constant | The constant. A spike's center falls as the window grows from 3 to 7, and stays positive |
| Gaussian numbers | Unit test recomputes the interval rule and the `k/5` weights; it does not call `smoothdata` to build the expected vector |
| FD001 zip | Still only under `downloads/cmapss/`. The story reads through `load_fd001` |
| Existing tests | Not modified |
