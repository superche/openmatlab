# Acceptance evidence: Epic #699 (D-E2 debug engine: breakpoints, stepping, paused workspace)

**Epic:** [#699](https://github.com/superche/openmatlab/issues/699)  
**Feature PR:** [#714](https://github.com/superche/openmatlab/pull/714) (#699, #699, #699, #713)  
**Milestone:** [Debugger and Workbench (M11)](https://github.com/superche/openmatlab/milestone/11) · [`docs/milestones/M11-debugger-workbench.md`](../milestones/M11-debugger-workbench.md)  
**Design + adversarial review:** [`docs/design/EPIC-699-pause-model.md`](../design/EPIC-699-pause-model.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `e0b864899d4d3217662e207fd843765e3b51da72` | Squash merge of feature PR [#714](https://github.com/superche/openmatlab/pull/714) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M11 criterion D04 is **met**. Epic #699 stays **open** until the user accepts it.

D03, D04 and D05 are all met by this epic (D03/D05 gates in the targeted run below). The pause-model design doc was committed first on the feature branch.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| D03 breakpoints | #699 | [#714](https://github.com/superche/openmatlab/pull/714) | [job 116799650113](https://github.com/superche/openmatlab/actions/runs/38846989700/job/116799650113) **success** |
| D04 stepping | #699 | [#714](https://github.com/superche/openmatlab/pull/714) | same job |
| D05 paused workspace | #699 | [#714](https://github.com/superche/openmatlab/pull/714) | same job |
| residual | #713 | [#714](https://github.com/superche/openmatlab/pull/714) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "addpath('/tmp/t2'); dbstop in q2 at 3; dbstatus; s = dbstatus('q2'); s.line, dbclear all"
Breakpoint for q2 is on line 3.
ans =

3
$ openmatlab -e "dbcont"
error: dbcont: only valid when stopped at a breakpoint (K>> prompt).
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1565 passed, 2 deselected, 13 xfailed in 17.13s
$ pytest tests/unit/test_debugger.py tests/bdd/test_debugger_bdd.py "tests/conformance/test_m11_conformance.py::test_m11_criterion[D03-m11_d03_breakpoints]" "tests/conformance/test_m11_conformance.py::test_m11_criterion[D05-m11_d05_paused_workspace]" "tests/conformance/test_m11_conformance.py::test_m11_criterion[D04-m11_d04_stepping]" --tb=no
22 passed in 0.96s
$ pytest tests/conformance/test_m11_conformance.py --tb=no
6 passed, 5 xfailed in 0.39s
```

New cases: `tests/unit/test_debugger.py` (19), `tests/bdd/test_debugger_bdd.py` (2), M11 D03/D04/D05 conformance flipped to met. Interactive transcript (stdin piped to `openmatlab`): breakpoint hit prints `3   y = y * 2;`, `K>>` evaluates in the paused frame, `dbquit` returns to `>>`.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F runtime.debugger
runtime.debugger                 runtime    done     debug engine — dbstop/dbclear/dbstatus, dbstep/dbcont/dbquit, dbup/dbdown, K>> prompt
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| end-line stops, anonymous-function breakpoints, dbstop(struct), for-header stepping, dbup/dbdown N | [#713](https://github.com/superche/openmatlab/issues/713) |

## Milestone progress (M11)

- Criteria met: **5 / 10** (D01, D02, D03, D04, D05)
- Conformance scripts passing: **5 / 10** (strict xfail pending: D06, D07, D08, D09, D10)
- Next: T-E2 #692 / T-E4 #694, then D-E4 #701 (Workbench debug UI).
