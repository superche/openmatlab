# Acceptance evidence: Epic #773 (G-E6 figure files and export)

**Epic:** [#773](https://github.com/superche/openmatlab/issues/773)  
**Feature PR:** [#980](https://github.com/superche/openmatlab/pull/980) (#773, #593); G08 completed by [#982](https://github.com/superche/openmatlab/pull/982) (`saveas` `.fig`, Shaw)  
**Milestone:** [Graphics completion (M13)](https://github.com/superche/openmatlab/milestone/13) · [`docs/milestones/M13-graphics.md`](../milestones/M13-graphics.md)  
**Design + adversarial review:** [`docs/design/EPIC-773-fig-export.md`](../design/EPIC-773-fig-export.md)  
**Captured:** 2026-10-17 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip (savefig/openfig/export/print) | `993e29d278e9b7ba3f0b9ba28cc63400947b09d9` | Squash merge of [#980](https://github.com/superche/openmatlab/pull/980) |
| Functional tip (`saveas` `.fig` + G08) | `47afebc19b4a87a122fed40f079ebf1970db0894` | Squash merge of [#982](https://github.com/superche/openmatlab/pull/982) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M13 criterion **G08** is **met**. Epic #773 stays **open** until the user accepts it.

Own `.fig` format (zipped JSON property tree; incompatible with MATLAB `.fig`): `savefig`/`openfig`/`hgsave`/`hgload` with zero property-tree diff; `exportgraphics`; `print -dDEVICE -rN`. `saveas(h,'x.fig')` writes the same own format (Shaw-approved #979/#982).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| G-E6 epic: savefig/openfig/exportgraphics/print | #773 | [#980](https://github.com/superche/openmatlab/pull/980) | [job 117324006411](https://github.com/superche/openmatlab/actions/runs/39007896983/job/117324006411) **success** |
| `saveas` `.fig` (Shaw #979) | #979 | [#982](https://github.com/superche/openmatlab/pull/982) | [job 117327620479](https://github.com/superche/openmatlab/actions/runs/39009121332/job/117327620479) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "d=tempname; mkdir(d); f=figure('Visible','off'); plot(1:3,'Tag','k'); savefig(f,fullfile(d,'a.fig')); close(f); g=openfig(fullfile(d,'a.fig'),'invisible'); l=findobj(g,'Tag','k'); disp(l.LineWidth); saveas(g,fullfile(d,'c.fig')); disp(isfile(fullfile(d,'c.fig'))); close all; rmdir(d,'s')"
0.5000
1
```

## Measurable gate: pytest

```text
$ pytest tests/unit/test_epic773_figio.py --tb=no
============================== 16 passed in 4.70s ==============================
$ pytest tests/conformance/test_m13_conformance.py --tb=no
============================= 11 passed in 22.00s ==============================
```

G08 flipped to met after #982.

**Existing tests changed:** `test_saveas_png_and_unsupported_fig` (Shaw-approved #979).

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.graphics.figio
libs.graphics.figio              libs       done     Figure files (own .fig format) and export
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Struct/cell/object `UserData` dropped on save (listed in file `dropped`) | by design (documented) |
| MATLAB `.fig` binary compatibility | none (M13 non-goal) |

## Milestone progress (M13)

- Criteria met: **10 / 10**
- Conformance scripts passing: **11 / 11**
- Next: epic acceptance; M12 C08 T3
