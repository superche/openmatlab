# Acceptance evidence — Epic #372 (MATLAB-aligned Workbench)

**Epic:** [#372 Epic: MATLAB-aligned Workbench (Host product + plugin slots)](https://github.com/superche/openmatlab/issues/372)  
**Scope issues:** [#377](https://github.com/superche/openmatlab/issues/377) · [#378](https://github.com/superche/openmatlab/issues/378) · [#379](https://github.com/superche/openmatlab/issues/379) · [#380](https://github.com/superche/openmatlab/issues/380) · [#381](https://github.com/superche/openmatlab/issues/381) · [#382](https://github.com/superche/openmatlab/issues/382)  
**Milestone:** [MATLAB-aligned Workbench](https://github.com/superche/openmatlab/milestone/6) · [`docs/milestones/M-workbench-aligned.md`](../milestones/M-workbench-aligned.md)  
**Captured:** 2026-10-12 ~10:34 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional (W01–W06) | `70acb2361de19e2d134e81b2663af9eb9c45ec0f` | Squash merge of [#387](https://github.com/superche/openmatlab/pull/387) |
| Evidence (this PR) | *(fill after merge)* | Acceptance + window recording |

## Verdict

**Ready for user acceptance.** Milestone exit criteria 1–4 hold on `main` (W01–W06 **met**, no open `p0` on milestone/6). Children #377–#382 closed. **Epic remains OPEN** until the user accepts.

## Traceability — Issues → PR → CI

| Criterion | Issue | PR | CI (`test`) |
|-----------|-------|----|-------------|
| W01 Host shell | #377 | [#383](https://github.com/superche/openmatlab/pull/383) | prior (first slice) |
| W02 Command Window | #378 | [#383](https://github.com/superche/openmatlab/pull/383) | prior |
| W03 Editor | #379 | [#387](https://github.com/superche/openmatlab/pull/387) | [run 38196206681](https://github.com/superche/openmatlab/actions/runs/38196206681) **success** |
| W04 Workspace browser | #380 | [#387](https://github.com/superche/openmatlab/pull/387) | same |
| W05 Current Folder | #381 | [#387](https://github.com/superche/openmatlab/pull/387) | same |
| W06 Figure management | #382 | [#387](https://github.com/superche/openmatlab/pull/387) | same |

Functional tip check-run: name=`test`, conclusion=`success`,  
https://github.com/superche/openmatlab/actions/runs/38196206681/job/114639292374

## Milestone progress (M-workbench-aligned)

- Criteria met: **6 / 6** (W01–W06)
- Remaining gaps on this milestone: *(none — residuals deferred if IDE/LSP breadth grows)*

## Feature map (epic-related)

| feature_id | status |
|------------|--------|
| `host.workbench.shell` | partial |
| `host.workbench.command_window` | partial |
| `host.workbench.editor` | partial |
| `host.workbench.workspace_browser` | partial |
| `host.workbench.current_folder` | partial |
| `host.workbench.figures` | partial |

`partial` = MVP panels + tests; not full IDE (no LSP/debugger).

## Measurable gate — pytest markers

```text
$ pytest -m "unit or bdd" --tb=no
389 passed, 2 deselected, 1 warning in 1.60s
```

Never weakened.

## Smoke — layout regions

```text
$ openmatlab workbench --list-only
ID                           TITLE              KIND     STATUS
----------------------------------------------------------------------
command_window               Command Window     host     ready
editor                       Editor             host     ready
workspace_browser            Workspace          host     ready
current_folder               Current Folder     host     ready
figures                      Figures            host     ready
```

## Smoke — Command Window eval

```text
$ openmatlab workbench --eval 'z = [9 8 7]'
z =

[[9. 8. 7.]]
```

## Window recording (E2E)

- Video: [`demos/workbench/showcase_workbench.mp4`](../../demos/workbench/showcase_workbench.mp4) (~21s)
- Helper: `demos/workbench/record_showcase.sh`
- Shows: `--list-only` (all ready) → headless `--eval` → tk Host window with
  scripted walkthrough (CW eval, Workspace, Current Folder open `.m`, Editor,
  Figures list/close/focus surface)

```bash
DISPLAY=:2 ./demos/workbench/record_showcase.sh
```

## Residuals / non-goals

- Full IDE (LSP, debugger) — explicitly out of W03 scope
- Browser/web workbench (Option D)
- Marketplace
- Closing Epic #349 — separate user acceptance

No residual gap Issues required for this MVP gate (criteria table complete).

## Architecture

See `docs/milestones/M-workbench-aligned.md` and `docs/design/M6-workbench-first.md`.
