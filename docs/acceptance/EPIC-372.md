# Acceptance evidence — Epic #372 (MATLAB-aligned Workbench)

**Epic:** [#372 Epic: MATLAB-aligned Workbench (Host product + plugin slots)](https://github.com/superche/openmatlab/issues/372)  
**Scope issues:** [#377](https://github.com/superche/openmatlab/issues/377)–[#382](https://github.com/superche/openmatlab/issues/382) (panel MVP) · [#390](https://github.com/superche/openmatlab/issues/390)–[#398](https://github.com/superche/openmatlab/issues/398) (layout parity)  
**Milestone:** [MATLAB-aligned Workbench](https://github.com/superche/openmatlab/milestone/6) · [`docs/milestones/M-workbench-aligned.md`](../milestones/M-workbench-aligned.md)  
**Captured:** 2026-10-12 ~10:47 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Layout parity (W07–W15) | `397bc3215b79266d4727775f14295082b0a7d67d` | Squash merge of [#399](https://github.com/superche/openmatlab/pull/399) |
| Evidence (docs + sample) | `7ce9d65fea0a7032209e62a6db57d803584c9a3c` | Squash merge of [#400](https://github.com/superche/openmatlab/pull/400) |
| Prior panel MVP (W01–W06) | `70acb2361de19e2d134e81b2663af9eb9c45ec0f` | Squash merge of [#387](https://github.com/superche/openmatlab/pull/387) |

## Verdict

**Ready for user acceptance (Desktop layout parity).** Panel MVP + layout parity criteria met on `main`. Children #377–#382 and #390–#398 closed. **Epic remains OPEN** until the user accepts.

## Honest split

| Tier | Criteria | Status |
|------|----------|--------|
| Panel MVP | W01–W06 | **met** |
| Layout parity | W07–W15 | **met** |

Milestone exit now requires MATLAB-like layout parity (not panel MVP alone).

## Traceability — Issues → PR → CI

| Criterion | Issue | PR | CI (`test`) |
|-----------|-------|----|-------------|
| W01–W02 | #377 #378 | [#383](https://github.com/superche/openmatlab/pull/383) | prior |
| W03–W06 | #379–#382 | [#387](https://github.com/superche/openmatlab/pull/387) | prior |
| W07–W15 | #390–#398 | [#399](https://github.com/superche/openmatlab/pull/399) | [run 38197078130](https://github.com/superche/openmatlab/actions/runs/38197078130) **success** |

Functional tip check-run: name=`test`, conclusion=`success`,  
https://github.com/superche/openmatlab/actions/runs/38197078130/job/114642019796

## Milestone progress (M-workbench-aligned)

- Panel MVP met: **6 / 6** (W01–W06)
- Layout parity met: **9 / 9** (W07–W15)
- Remaining gaps on this milestone: *(none open; #372 OPEN for user accept)*

## Feature map (epic-related)

| feature_id | status |
|------------|--------|
| `host.workbench.shell` | partial |
| `host.workbench.command_window` | partial |
| `host.workbench.editor` | partial |
| `host.workbench.workspace_browser` | partial |
| `host.workbench.current_folder` | partial |
| `host.workbench.figures` | partial |

`partial` = Desktop chrome + panels + tests; not full IDE (no LSP/debugger; not pixel-perfect ribbon).

## Measurable gate — pytest markers

```text
$ pytest -m "unit or bdd" --tb=no
395 passed, 2 deselected, 1 warning in 1.76s
```

Never weakened (+5 layout-parity unit tests).

## Smoke — layout regions + docks

```text
$ openmatlab workbench --list-only
ID                           TITLE              KIND     DOCK     STATUS
--------------------------------------------------------------------------------
command_window               Command Window     host     bottom   ready
editor                       Editor             host     center   ready
workspace_browser            Workspace          host     right    ready
current_folder               Current Folder     host     left     ready
figures                      Figures            host     right    ready
```

## Window recording (E2E) — Desktop chrome

- Video: [`demos/workbench/showcase_workbench.mp4`](../../demos/workbench/showcase_workbench.mp4) (~22s)
- Helper: `demos/workbench/record_showcase.sh`
- Shows: `--list-only` (DOCK column) → headless `--eval` → tk **Desktop** window
  (menu bar, toolstrip, path toolbar, CF left, multi-doc Editor center, CW bottom
  with history, Workspace Value + docked Figures right)

```bash
DISPLAY=:2 ./demos/workbench/record_showcase.sh
```

## Residuals / non-goals

- Full IDE (LSP, debugger)
- Browser/web workbench (Option D)
- Marketplace / pixel-perfect MathWorks ribbon
- Layout persistence across process (W15 in-memory Default only)
- Closing Epic #349 — separate user acceptance

## Architecture

See `docs/milestones/M-workbench-aligned.md` and `docs/design/M6-workbench-first.md`.
