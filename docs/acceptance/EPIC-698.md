# Acceptance evidence: Epic #698 (D-E1 call stack: MException.stack, getReport, dbstack)

**Epic:** [#698](https://github.com/superche/openmatlab/issues/698)  
**Feature PR:** [#706](https://github.com/superche/openmatlab/pull/706) (#698, #698, #705)  
**Milestone:** [Debugger and Workbench (M11)](https://github.com/superche/openmatlab/milestone/11) · [`docs/milestones/M11-debugger-workbench.md`](../milestones/M11-debugger-workbench.md)  
**Design + adversarial review:** [`docs/design/EPIC-698-callstack.md`](../design/EPIC-698-callstack.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `a060296b5a7be55459f7d708df78a9e23e331a13` | Squash merge of feature PR [#706](https://github.com/superche/openmatlab/pull/706) |
| Evidence merge tip | `7940d9c2853c29b6b167a4140d261d837800ad22` | Squash merge of [#707](https://github.com/superche/openmatlab/pull/707); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M11 criterion D01 is **met**. Epic #698 stays **open** until the user accepts it.

D01 and D02 are both met by this epic (D02 gate: `test_m11_criterion[D02-m11_d02_dbstack]` in the targeted run below). Absorbed parts of #565 (MException.stack/getReport) and #611 (dbstack) are delivered; those issues stay on Core backlog for their remaining items.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| D01 MException.stack / getReport | #698 | [#706](https://github.com/superche/openmatlab/pull/706) | [job 116792343516](https://github.com/superche/openmatlab/actions/runs/38844665177/job/116792343516) **success** |
| D02 dbstack / mfilename | #698 | [#706](https://github.com/superche/openmatlab/pull/706) | same job |
| residual | #705 | [#706](https://github.com/superche/openmatlab/pull/706) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "addpath('/tmp/t1'); try, f1(); catch e, end; disp(getReport(e)); s = e.stack(1)"
Error using f1>g (line 6)
boom 1

Error in f1 (line 3)
s =

  struct with fields:

    file: '/tmp/t1/f1.m'
    name: 'f1>g'
    line: 6
$ openmatlab -e "addpath('/tmp/t1'); f1()"
error: boom 1
Error in f1>g (line 6)
Error in f1 (line 3)
$ openmatlab -e "c = {1,'a'}'; size(c)"
ans =

   2   1
$ openmatlab -e "m = mfilename"
m =
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1514 passed, 2 deselected, 18 xfailed in 18.00s
$ pytest tests/unit/test_callstack.py tests/bdd/test_callstack_bdd.py "tests/conformance/test_m11_conformance.py::test_m11_criterion[D02-m11_d02_dbstack]" "tests/conformance/test_m11_conformance.py::test_m11_criterion[D01-m11_d01_exception_stack_report]" --tb=no
14 passed in 0.86s
$ pytest tests/conformance/test_m11_conformance.py --tb=no
3 passed, 8 xfailed in 0.42s
```

New cases: `tests/unit/test_callstack.py` (10), `tests/bdd/test_callstack_bdd.py` (2), M11 D01/D02 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F runtime.callstack
runtime.callstack                runtime    done     call stack — MException.stack lines, getReport, dbstack, mfilename, "Error in" reports
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| builtin-named 'Error using' header, nested/anonymous frame names, continuation lines, property-default frames, error(struct) stack | [#705](https://github.com/superche/openmatlab/issues/705) |

## Milestone progress (M11)

- Criteria met: **2 / 10** (D01, D02)
- Conformance scripts passing: **2 / 10** (strict xfail pending: D03, D04, D05, D06, D07, D08, D09, D10)
- Next: T-E1 #691 (M10 T01/T02), then D-E2 #699 (pause-model design doc first).
