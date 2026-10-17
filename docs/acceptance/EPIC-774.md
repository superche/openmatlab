# Acceptance evidence: Epic #774 (G-E7 Workbench figure docking + snapshots)

**Epic:** [#774](https://github.com/superche/openmatlab/issues/774)  
**Feature PR:** [#981](https://github.com/superche/openmatlab/pull/981) (#774)  
**Milestone:** [Graphics completion (M13)](https://github.com/superche/openmatlab/milestone/13) · [`docs/milestones/M13-graphics.md`](../milestones/M13-graphics.md)  
**Design + adversarial review:** [`docs/design/EPIC-774-docking-snapshots.md`](../design/EPIC-774-docking-snapshots.md)  
**Captured:** 2026-10-17 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `b1b846e597274d7e2ed04b0bb95b411e05289b5a` | Squash merge of feature PR [#981](https://github.com/superche/openmatlab/pull/981) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M13 criteria **G09** and **G10** are **met**. Epic #774 stays **open** until the user accepts it.

G09 second half: figures with `WindowStyle` `'docked'` appear in the Workbench Figures panel (list + PNG previews); a new figure takes focus via `FigureManager` / `gcf`. `DefaultFigureWindowStyle` and other `Default<Type><Prop>` on root/figure/axes. G09 first half (output routing) was Epic #767. G10: 46 own golden PNG scenes under `tests/conformance/golden/snapshots/`, Agg + DejaVu Sans + DPI 100, CIE76 ΔE (≤ 1 % pixels > 10) or SSIM ≥ 0.98; digests stable across re-runs.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| G-E7 epic: docking, focus, Default*, golden snapshots | #774 | [#981](https://github.com/superche/openmatlab/pull/981) | [job 117326662831](https://github.com/superche/openmatlab/actions/runs/39008799028/job/117326662831) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "set(groot,'DefaultFigureWindowStyle','docked'); figure; plot(1:5); figure; plot(1:3); disp(get(gcf,'Number')); set(groot,'DefaultFigureWindowStyle','normal'); close all"
2
$ openmatlab -e "f=figure('Visible','off'); plot(1:10); print(f,'/tmp/acc774.png','-dpng'); disp(exist('/tmp/acc774.png','file')); close all"
2
```

## Measurable gate: pytest

```text
$ pytest tests/conformance/test_m13_conformance.py --tb=no
============================= 11 passed in 22.00s ==============================
$ pytest tests/unit/test_epic774_docking_defaults.py tests/unit/test_epic774_snapshots.py --tb=no
============================= 12 passed in 30.37s ==============================
```

New cases: `tests/unit/test_epic774_docking_defaults.py`, `tests/unit/test_epic774_snapshots.py`; G09/G10 flipped to met.

**Existing tests changed: none** (in #981).

## Feature map (epic-related)

```text
$ openmatlab features | rg -F -e host.workbench.figures -e libs.graphics.defaults -e qa.snapshots
host.workbench.figures           host       done     Workbench figure management
libs.graphics.defaults           libs       done     Default<Type><Prop> on root/figure/axes
qa.snapshots                     qa         done     Golden image snapshot infrastructure
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| tkinter not available on this agent box for GUI figure-panel recording (CI/ubuntu has it; model + conformance verified) | none (env) |
| Pixel parity with MATLAB | none (M13 non-goal) |

## Milestone progress (M13)

- Criteria met: **10 / 10** (all G01–G10; G05/G08 completed by Shaw-approved #982)
- Conformance scripts passing: **11 / 11** (0 xfail)
- Next: acceptance of open epics; M12 C08 T3; corpus re-run REPORT
