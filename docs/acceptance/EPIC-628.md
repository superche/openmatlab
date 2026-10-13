# Acceptance evidence: Epic #628 (descriptive statistics)

**Epic:** [#628](https://github.com/superche/openmatlab/issues/628)  
**Feature PR:** [#662](https://github.com/superche/openmatlab/pull/662) (#628)  
**Milestone:** [Domain toolboxes (M3)](https://github.com/superche/openmatlab/milestone/3) · [`docs/milestones/M3-domain-toolboxes.md`](../milestones/M3-domain-toolboxes.md)  
**Design + adversarial review:** [`docs/design/EPIC-628-stats.md`](../design/EPIC-628-stats.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `6009d306b9fe2ad2dac8eb2051769732e5ea4dcc` | Squash merge of feature PR [#662](https://github.com/superche/openmatlab/pull/662) |
| Evidence merge tip | `21741f09423079a316dd9dda430681dbc55b03a8` | Squash merge of [#663](https://github.com/superche/openmatlab/pull/663); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M3 criterion T04 is **met**. Epic #628 stays **open** until the user accepts it.

Covered:
- `quantile`/`prctile` with MATLAB's exact method, dim/'all', NaN ignored;
- `movmean`/`movsum`/`movmedian` plus `movmax`/`movmin`/`movprod`/`movvar`/`movstd`, scalar and [kb kf] windows, Endpoints, omitnan, dim;
- `histc` with bin-index output;
- `cummax`/`cummin`, `mode`, `var`/`std` weights and `bounds` (already in core since Epic #534) verified by the T04 script.

This absorbs the stats part of #581.

T04 is met.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| M3-E4 descriptive statistics (T04) | #628 | [#662](https://github.com/superche/openmatlab/pull/662) | [job 115216274267](https://github.com/superche/openmatlab/actions/runs/38373583595/job/115216274267) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "quantile([2 4 6 8 10], [0.25 0.5 0.9])"
ans =

    3.5000    6.0000   10.0000
$ openmatlab -e "prctile([1 2; 3 4; 5 6], 50)"
ans =

   3   4
$ openmatlab -e "movmean(1:6, 4)"
ans =

   1.5000   2.0000   2.5000   3.5000   4.5000   5.0000
$ openmatlab -e "movsum([1 2 3 4 5], 3, 'Endpoints', 'discard')"
ans =

    6    9   12
$ openmatlab -e "movmedian([1 5 2 8 3], 3)"
ans =

   3.0000   2.0000   5.0000   3.0000   5.5000
$ openmatlab -e "[n, bin] = histc([0 1 1.5 3 4], [1 2 4])"
n =

   2   1   1

bin =

   0   1   1   2   3
$ openmatlab -e "var([1 2 3 4], [1 1 1 1])"
ans =

1.2500
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1439 passed, 2 deselected, 7 xfailed in 18.51s
$ pytest tests/unit/test_stats_m3.py tests/bdd/test_stats_m3_bdd.py "tests/conformance/test_m3_conformance.py::test_m3_criterion[T04-m3_t04_stats]" --tb=no
6 passed in 0.42s
$ pytest tests/conformance/test_m3_conformance.py --tb=no
5 passed, 3 xfailed in 0.53s
```

New cases: 3 unit tests (`tests/unit/test_stats_m3.py`), 2 Gherkin scenarios (`features/stats_m3.feature`), and conformance `m3_t04_stats` (18 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F numerics.stats_m3
numerics.stats_m3                numerics   done     quantile/prctile, movmean/movsum/movmedian (and movmax/movmin/movprod/movvar/movstd), histc
```

## Residuals (filed)

- [#661](https://github.com/superche/openmatlab/issues/661) (p2): mov* SamplePoints, quantile 'approximate', mode third output, histc on char/datetime.
- [#581](https://github.com/superche/openmatlab/issues/581): its stats part (prctile/quantile/histc) is now delivered; the integral/fminsearch options part was delivered in M3-E3 (#627).

## Milestone progress (M3)

- Criteria met: **4 / 7** (T01, T02, T03, T04)
- Conformance scripts passing: **4 / 7** (strict xfail pending: T05, T06, T07)
- Next: M3-E5 JSON and delimited numeric I/O (#629)
