# Acceptance evidence: Epic #703 (D-E6 Workbench workflows)

**Epic:** [#703](https://github.com/superche/openmatlab/issues/703)  
**Feature PR:** [#752](https://github.com/superche/openmatlab/pull/752) (#703, #751)  
**Milestone:** [Debugger and Workbench (M11)](https://github.com/superche/openmatlab/milestone/11) · [`docs/milestones/M11-debugger-workbench.md`](../milestones/M11-debugger-workbench.md)  
**Design + adversarial review:** [`docs/design/EPIC-703-workbench-workflows.md`](../design/EPIC-703-workbench-workflows.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `a7de8fb64143af5cbada728e11a039e835890f76` | Squash merge of feature PR [#752](https://github.com/superche/openmatlab/pull/752) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M11 criterion D10 is **met**. Epic #703 stays **open** until the user accepts it.

D10 is met on the headless Workbench model: `%%` sections, Run Section and Run and Advance, run with breakpoints, the error hyperlink (file and line of the top frame, opened in the Editor) and Command History re-run. The tk chrome (toolstrip buttons, Ctrl+Enter, clickable `Error in` lines, Command History list) is driven by `test_tk_workflow_chrome` under a display.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| D10 sections / run section / error link / history re-run | #703 | [#752](https://github.com/superche/openmatlab/pull/752) | [job 116832200466](https://github.com/superche/openmatlab/actions/runs/38857518578/job/116832200466) **success** |
| residual | #751 | [#752](https://github.com/superche/openmatlab/pull/752) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "d = tempname; mkdir(d); fid = fopen(fullfile(d,'bad703.m'),'w'); fprintf(fid,'function bad703()\n  x = 1;\n  error(''d10:e'', ''oops'');\nend\n'); fclose(fid); addpath(d); bad703()"
error: oops
Error in bad703 (line 3)
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1762 passed, 2 deselected, 1 xfailed in 18.37s
$ pytest tests/unit/test_workbench_workflows.py tests/bdd/test_workbench_workflows_bdd.py "tests/conformance/test_m11_conformance.py::test_m11_criterion[D10-m11_d10_workbench_workflows]" --tb=no
11 passed in 0.67s
$ pytest tests/conformance/test_m11_conformance.py --tb=no
11 passed in 0.47s
```

New cases: `tests/unit/test_workbench_workflows.py` (8, incl. tk smoke), `tests/bdd/test_workbench_workflows_bdd.py` (2), M11 D10 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F host.workbench.workflows
host.workbench.workflows         host       done     Workbench workflows
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Section-relative error lines, section highlighting, recorded video capture, history search, unsaved-buffer breakpoints | [#751](https://github.com/superche/openmatlab/issues/751) |

## Milestone progress (M11)

- Criteria met: **10 / 10** (D01, D02, D03, D04, D05, D06, D07, D08, D09, D10)
- Conformance scripts passing: **10 / 10** (strict xfail pending: none)
- Next: T-E7 #697 timetable (M10).
