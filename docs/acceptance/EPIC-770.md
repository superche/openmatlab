# Acceptance evidence: Epic #770 (G-E3 axes layout)

**Epic:** [#770](https://github.com/superche/openmatlab/issues/770)  
**Feature PR:** [#914](https://github.com/superche/openmatlab/pull/914) (#770, #593)  
**Milestone:** [Graphics completion (M13)](https://github.com/superche/openmatlab/milestone/13) · [`docs/milestones/M13-graphics.md`](../milestones/M13-graphics.md)  
**Design + adversarial review:** [`docs/design/EPIC-770-layout.md`](../design/EPIC-770-layout.md)  
**Captured:** 2026-10-17 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `518d93441371f009a79ad4a1d7988c394b77280b` | Squash merge of feature PR [#914](https://github.com/superche/openmatlab/pull/914) |
| Evidence merge tip | `78d85759676eba3369db47706c1b3b10a4b087e3` | Squash merge of [#975](https://github.com/superche/openmatlab/pull/975); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M13 criterion G03 is **met**. Epic #770 stays **open** until the user accepts it.

`tiledlayout` (grid, `'flow'`/`'vertical'`/`'horizontal'`, `TileSpacing`/`Padding`/`TileIndexing`) with `nexttile` (index, span, first empty tile) and class `matlab.graphics.layout.TiledChartLayout`; `yyaxis left|right` with per-side limits and replace-mode plotting; `subplot` positions from our own grid rule with overlap-only replacement and `subplot('Position', pos)`; nice auto limits (1/2/5 x 10^k steps, whole decades on log axes; our own documented approximation); `axis equal/image/square/normal/tight/ij/xy/off` set the MATLAB properties. This also covers the corpus `plotyy` graphics failures through `yyaxis`.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| G-E3 epic: tiledlayout/nexttile, yyaxis, subplot geometry, nice limits, axis modes | #770 | [#914](https://github.com/superche/openmatlab/pull/914) | [job 117313817763](https://github.com/superche/openmatlab/actions/runs/39004411117/job/117313817763) **success** |
| graphics residuals: nice ticks, yyaxis | #593 | [#914](https://github.com/superche/openmatlab/pull/914) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "t = tiledlayout(2,2); ax = nexttile; disp(class(t)); yyaxis left; plot(1:3); yyaxis right; plot([10 20 30]); disp(ax.YAxisLocation); axis equal; disp(get(gca,'DataAspectRatio')); close all"
matlab.graphics.layout.TiledChartLayout
right
   1   1   1
$ openmatlab -e "f = figure('Visible','off'); plot([0.3 9.7]); disp(ylim); a1 = subplot(2,1,1); disp(round(a1.Position*1000)/1000); axis tight; disp(get(gca,'XLimMode')); close all"
    0   10
   0.1300   0.5730   0.7750   0.3530
manual
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
2153 passed, 14 deselected, 5 xfailed in 75.42s (0:01:15)
$ pytest tests/unit/test_epic770_layout.py "tests/conformance/test_m13_conformance.py::test_m13_criterion[G03-m13_g03_layout_axes]" --tb=no
14 passed in 3.06s
$ pytest tests/conformance/test_m13_conformance.py --tb=no
7 passed, 4 xfailed in 2.16s
```

New cases: `tests/unit/test_epic770_layout.py` (13 cases); G03 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.graphics.layout
libs.graphics.layout             libs       done     Axes layout (tiledlayout, nexttile, yyaxis, subplot geometry, nice limits, axis modes)
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Tick picker and `subplot` geometry are our own documented approximations, not MATLAB's pixel layout | none (by design, M13 non-goal: pixel parity) |

## Milestone progress (M13)

- Criteria met: **6 / 10** (G01, G02, G03, G04, G06, G07)
- Conformance scripts passing: **6 / 10** (strict xfail pending: G05 (#866, awaits Shaw), G08, G09, G10)
- Next: G-E4 #771 remaining properties, G-E6 #773 (G08), G-E7 #774 (G09/G10); G05 waits for Shaw on #866.
