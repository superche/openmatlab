# Acceptance evidence: Epic #772 (G-E5 2-D charts and annotations)

**Epic:** [#772](https://github.com/superche/openmatlab/issues/772)  
**Feature PR:** [#855](https://github.com/superche/openmatlab/pull/855) (#772, #857)  
**Milestone:** [Graphics completion (M13)](https://github.com/superche/openmatlab/milestone/13) · [`docs/milestones/M13-graphics.md`](../milestones/M13-graphics.md)  
**Design + adversarial review:** [`docs/design/EPIC-772-charts2d.md`](../design/EPIC-772-charts2d.md)  
**Captured:** 2026-10-17 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `fbc078ae3f81bb164bc89de1e93135578b6878ee` | Squash merge of feature PR [#855](https://github.com/superche/openmatlab/pull/855) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M13 criterion G04 is **met**. Epic #772 stays **open** until the user accepts it.

2-D chart breadth: `errorbar`, `area`, `stairs`, `stem`, `pie`, `barh` and matrix `bar` (grouped/stacked), `hist`, `patch`/`fill`, `rectangle`, `line`, `image`/`imagesc`, `pcolor`, `contour`/`contourf`, `quiver`, `spy`, `polar`/`polarplot`/`rose`/`compass`, `plotyy`, `loglog`/`semilogx`/`semilogy`, and `axes`, `zlabel`, `box`, `drawnow`. Annotations: 3-D `text` with Interpreter, `annotation` shapes, `colorbar`. Colormap tables (`parula`/`turbo` are clean-room approximations) and `caxis`/`clim`. Documented properties (`Units`, `XTick`, `XDir`, `Interpreter`, ...) are stored with their documented defaults. Unknown names still raise. G07's last check (`findobj`) is delivered by G-E2 #769.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| G-E5 epic: 2-D charts, annotations, colormaps, documented properties | #772 | [#855](https://github.com/superche/openmatlab/pull/855) | [job 117174737326](https://github.com/superche/openmatlab/actions/runs/38960705487/job/117174737326) **success** |
| residual | #857 | [#855](https://github.com/superche/openmatlab/pull/855) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "figure('Visible','off'); e = errorbar(1:3,[2 3 4],[1 1 1]); disp(class(e)); b = bar([1 2;3 4],'stacked'); disp(numel(b)); p = pie([1 2 3]); disp(numel(p)); set(gca,'XTick',1:3); disp(get(gca,'XTick')); disp(gray(3)); close all"
matlab.graphics.chart.primitive.ErrorBar
2
6
   1   2   3
   0.0000   0.0000   0.0000
   0.5000   0.5000   0.5000
   1.0000   1.0000   1.0000
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1988 passed, 2 deselected, 11 xfailed in 82.97s (0:01:22)
$ pytest tests/unit/test_epic772_charts2d.py tests/bdd/test_graphics_charts2d_bdd.py "tests/conformance/test_m13_conformance.py::test_m13_criterion[G04-m13_g04_charts2d]" --tb=no
32 passed in 3.56s
$ pytest tests/conformance/test_m13_conformance.py --tb=no
3 passed, 8 xfailed in 1.65s
```

New cases: `tests/unit/test_epic772_charts2d.py` (29), `tests/bdd/test_graphics_charts2d_bdd.py` (2); G04 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.graphics.charts2d
libs.graphics.charts2d           libs       done     2-D chart breadth, annotations and colormaps
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| `xticks`/`yticks`, `imshow`, `title(colorbar,...)`, `@ishandle` handles, `colormap('name(n)')` | [#857](https://github.com/superche/openmatlab/issues/857) |
| 3-D charts (`surf`, `mesh`, `plot3`, `sphere`, `view`) | G-E4 [#771](https://github.com/superche/openmatlab/issues/771) (G06) |

## Milestone progress (M13)

- Criteria met: **2 / 10** (G01, G04)
- Conformance scripts passing: **2 / 10** (strict xfail pending: G02, G03, G05, G06, G07, G08, G09, G10)
- Next: G-E2 #769 (findobj; completes G07), G-E4 #771, G-E3 #770, G-E6 #773, G-E7 #774; M12 C-E5 #765.
