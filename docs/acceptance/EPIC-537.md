# Acceptance evidence: Epic #537 (graphics core)

**Epic:** [#537](https://github.com/superche/openmatlab/issues/537)  
**Feature PR:** [#594](https://github.com/superche/openmatlab/pull/594) (#557, #558, #559)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-537-graphics-core.md`](../design/EPIC-537-graphics-core.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `f42c74f0a557a050c38300fa2a912e95cd2dec8d` | Squash merge of feature PR [#594](https://github.com/superche/openmatlab/pull/594) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M7 criterion C08 is **met**. Epic #537 stays **open** until the user accepts it.

Covered:
- a MATLAB handle-graphics object tree (root/figure/axes/line/bar/scatter/histogram/text/legend) with `get`/`set` validation;
- MATLAB placement rules (`plot` reuses the current axes, `hold`, `subplot` slots);
- decorations, `grid`, `axis`/`xlim`/`ylim` with modes;
- `bar`/`scatter`/`histogram`, `saveas` to raster/vector formats.

Two existing tests changed with explicit user approval (plot returns a Line; plot reuses the current figure).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| graphics handle model: figure/axes/line objects with get/set, gca/gcf, close, saveas | #557 | [#594](https://github.com/superche/openmatlab/pull/594) | [job 115154486899](https://github.com/superche/openmatlab/actions/runs/38354618771/job/115154486899) **success** |
| hold subplot title xlabel ylabel legend grid axis xlim ylim | #558 | [#594](https://github.com/superche/openmatlab/pull/594) | same job |
| bar scatter histogram | #559 | [#594](https://github.com/superche/openmatlab/pull/594) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "p = plot(1:3, [1 4 9], 'r--'); t = get(p, 'Type'), c = get(p, 'Color'), ls = get(p, 'LineStyle')"
t =

line

c =

   1   0   0

ls =

--
$ openmatlab -e "plot(1:3); hold on; plot(1:2); n = numel(get(gca, 'Children')), nf = numel(get(0, 'Children'))"
n =

2

nf =

1
$ openmatlab -e "plot(1:3); axis([0 4 0 10]); lim = [xlim ylim]"
lim =

    0    4    0   10
$ openmatlab -e "h = histogram([1 2 2 3 3 3], 'BinEdges', [0.5 1.5 2.5 3.5]); v = get(h, 'Values')"
v =

   1   2   3
$ openmatlab -e "f = figure(7); n = get(f, 'Number'), s = subplot(2, 1, 2); k = numel(get(f, 'Children'))"
n =

7

k =

1
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1292 passed, 2 deselected, 2 xfailed in 19.45s
$ pytest tests/unit/test_handle_graphics.py tests/bdd/test_handle_graphics_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C08-m7_c08_graphics_core]" --tb=no
15 passed in 3.07s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
9 passed, 2 xfailed in 1.55s
```

New cases: 11 unit tests (`tests/unit/test_handle_graphics.py`), 3 Gherkin scenarios (`features/handle_graphics.feature`), 2 approved edits to existing tests, and conformance `m7_c08_graphics_core` (30+ checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.handle_graphics
libs.handle_graphics             libs       done     handle graphics core
```

## Residuals (filed)

- [#593](https://github.com/superche/openmatlab/issues/593) (p2): nice-tick auto limits, dot notation, .fig, 3-D, colorbar/colormap, findobj, axes(), yyaxis, more chart types.

## Milestone progress (M7)

- Criteria met: **8 / 10** (C01–C08)
- Conformance scripts passing: **8 / 10** (strict xfail pending: C09–C10)
- Next: Epic #538 (C09 linalg decompositions)
