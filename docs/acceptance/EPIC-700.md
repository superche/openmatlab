# Acceptance evidence: Epic #700 (D-E3 keyboard, input, condition stops)

**Epic:** [#700](https://github.com/superche/openmatlab/issues/700)  
**Feature PR:** [#730](https://github.com/superche/openmatlab/pull/730) (#700, #700, #729)  
**Milestone:** [Debugger and Workbench (M11)](https://github.com/superche/openmatlab/milestone/11) · [`docs/milestones/M11-debugger-workbench.md`](../milestones/M11-debugger-workbench.md)  
**Design + adversarial review:** [`docs/design/EPIC-700-condition-stops.md`](../design/EPIC-700-condition-stops.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `38e49d81b93ce183822ff1ea3d27a5d98527d1e5` | Squash merge of feature PR [#730](https://github.com/superche/openmatlab/pull/730) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M11 criterion D06 is **met**. Epic #700 stays **open** until the user accepts it.

D06 and D07 are both met by this epic (D07 gate: `test_m11_criterion[D07-m11_d07_error_stop]` in the conformance run below). The input/keyboard part of #577 is absorbed; #577 stays on the Core backlog untouched. Interactive pauses need typed input, so the live demos below cover only the non-interactive surface; the pause behaviour is evidenced by the D06/D07 conformance scripts (queued K>>/input lines) in the gates.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| D06 keyboard / input | #700 | [#730](https://github.com/superche/openmatlab/pull/730) | [job 116809911371](https://github.com/superche/openmatlab/actions/runs/38850332268/job/116809911371) **success** |
| D07 condition stops | #700 | [#730](https://github.com/superche/openmatlab/pull/730) | same job |
| residual | #729 | [#730](https://github.com/superche/openmatlab/pull/730) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "input()"
error: input requires a prompt: input(prompt) or input(prompt, 's').
$ openmatlab -e "keyboard(1)"
error: Too many input arguments.
$ openmatlab -e "dbstop if caught error d07:bad; dbstop if naninf; dbclear all; isempty(dbstatus)"
ans =

1
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1630 passed, 2 deselected, 8 xfailed in 18.40s
$ pytest tests/unit/test_condition_stops.py tests/bdd/test_condition_stops_bdd.py "tests/conformance/test_m11_conformance.py::test_m11_criterion[D06-m11_d06_keyboard_input]" --tb=no
11 passed in 0.41s
$ pytest tests/conformance/test_m11_conformance.py --tb=no
9 passed, 2 xfailed in 0.45s
```

New cases: `tests/unit/test_condition_stops.py` (8), `tests/bdd/test_condition_stops_bdd.py` (2), M11 D06/D07 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F runtime.condition_stops
runtime.condition_stops          runtime    done     keyboard, input and condition stops (error / caught error / warning / naninf)
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| naninf granularity, error-stop message fidelity, base-workspace stops, Workbench input prompt, condition stops in dbstatus | [#729](https://github.com/superche/openmatlab/issues/729) |

## Milestone progress (M11)

- Criteria met: **8 / 10** (D01, D02, D03, D04, D05, D06, D07, D08)
- Conformance scripts passing: **8 / 10** (strict xfail pending: D09, D10)
- Next: D-E5 #702 (variable editor) and T-E3 #693 / T-E5 #695.
