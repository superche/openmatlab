# EPIC-628: descriptive statistics (M3-E4)

Criterion **T04** (`m3_t04_stats`) in [M3](../milestones/M3-domain-toolboxes.md). The code is in core, in `openmatlab/libs/stats.py`. It also absorbs the prctile/quantile/histc part of #581. `cummax`/`cummin`, `mode`, `var`/`std` weights and `bounds` already shipped in Epic #534 and are covered by the T04 script unchanged.

## quantile / prctile
- MATLAB's default ('exact') method: sorted, NaN-free data of length n sit at cumulative probabilities `(i - 0.5)/n`; p is linearly interpolated and clamped to min/max outside `[0.5/n, 1 - 0.5/n]`. NaNs are ignored.
- Operates along the first non-singleton dimension, an explicit `dim`, or `'all'`; that dimension is replaced by `numel(p)`.
- p outside [0,1] ([0,100] for prctile) raises `MATLAB:quantile:BadPercents` / `MATLAB:prctile:BadPercents`.

## Moving windows
- `movmean movsum movmedian movmax movmin movprod movvar movstd`.
- Scalar k: odd centred `(k-1)/2` each side; even `k/2` back, `k/2-1` forward. `[kb kf]` explicit.
- `'Endpoints'`: 'shrink' (default), 'discard', 'fill' (NaN), numeric fill. `'includenan'` (default) / `'omitnan'`. `dim`.

## histc
- `edges(k) <= x < edges(k+1)`; the last bin counts `x == edges(end)`. Out-of-range and NaN get bin 0. Second output is the bin index. Matrices count per column (or along `dim`).

## Adversarial review
- Even windows are the classic off-by-one: the unit test pins `movmean(1:6,4)` to MATLAB's documented layout (first element = mean of the first two).
- Shrinking windows with `omitnan` can become empty: reducers return NaN (0 for sum, 1 for prod) instead of raising.
- Single-sample and all-NaN slices in quantile return the sample / NaN rather than interpolating on an empty grid.

## Tests
- `tests/unit/test_stats_m3.py`
- `features/stats_m3.feature`
- conformance `m3_t04_stats`

## Residuals
https://github.com/superche/openmatlab/issues/661
