# Acceptance evidence: Epic #701 (D-E4 Workbench debug UI)

**Epic:** [#701](https://github.com/superche/openmatlab/issues/701)  
**Feature PR:** [#726](https://github.com/superche/openmatlab/pull/726) (#701, #725)  
**Milestone:** [Debugger and Workbench (M11)](https://github.com/superche/openmatlab/milestone/11) · [`docs/milestones/M11-debugger-workbench.md`](../milestones/M11-debugger-workbench.md)  
**Design + adversarial review:** [`docs/design/EPIC-701-debug-ui.md`](../design/EPIC-701-debug-ui.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `9f9d41f415b02cdeaf1b43d3df23c6722214b21d` | Squash merge of feature PR [#726](https://github.com/superche/openmatlab/pull/726) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M11 criterion D08 is **met**. Epic #701 stays **open** until the user accepts it.

D08 is met by this epic on the headless Workbench model; the tk chrome (debug toolbar, stack selector, gutter, current-line marker) is driven by `test_tk_debug_chrome` under a display (it ran in the targeted gate below; it is skipped where no display exists).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| D08 gutter breakpoints / current line / toolbar / stack selector | #701 | [#726](https://github.com/superche/openmatlab/pull/726) | [job 116807507011](https://github.com/superche/openmatlab/actions/runs/38849553444/job/116807507011) **success** |
| residual | #725 | [#726](https://github.com/superche/openmatlab/pull/726) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "d = tempname; mkdir(d); fid = fopen(fullfile(d,'acc701.m'),'w'); fprintf(fid,'function y = acc701(x)\n  y = x * 2;\nend\n'); fclose(fid); addpath(d); dbstop in acc701 at 1; s = dbstatus('acc701'); s.line, dbclear all"
ans =

2
$ openmatlab -e "dbcont"
error: dbcont: only valid when stopped at a breakpoint (K>> prompt).
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1617 passed, 2 deselected, 10 xfailed in 18.16s
$ pytest tests/unit/test_workbench_debug.py tests/bdd/test_workbench_debug_bdd.py "tests/conformance/test_m11_conformance.py::test_m11_criterion[D08-m11_d08_workbench_debug_ui]" --tb=no
9 passed in 0.91s
$ pytest tests/conformance/test_m11_conformance.py --tb=no
7 passed, 4 xfailed in 0.47s
```

New cases: `tests/unit/test_workbench_debug.py` (6, incl. tk smoke), `tests/bdd/test_workbench_debug_bdd.py` (2), M11 D08 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F host.debug_ui
host.debug_ui                    host       done     Workbench debug UI — gutter breakpoints, current line, debug toolbar, stack selector
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Pause button for long runs, conditional breakpoints from the gutter, Step at function end | [#725](https://github.com/superche/openmatlab/issues/725) |

## Milestone progress (M11)

- Criteria met: **6 / 10** (D01, D02, D03, D04, D05, D08)
- Conformance scripts passing: **6 / 10** (strict xfail pending: D06, D07, D09, D10)
- Next: D-E3 #700 (keyboard/input/condition stops), then T-E3 #693 / T-E5 #695.
