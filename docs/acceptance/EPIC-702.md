# Acceptance evidence: Epic #702 (D-E5 variable editor panel)

**Epic:** [#702](https://github.com/superche/openmatlab/issues/702)  
**Feature PR:** [#748](https://github.com/superche/openmatlab/pull/748) (#702, #747)  
**Milestone:** [Debugger and Workbench (M11)](https://github.com/superche/openmatlab/milestone/11) · [`docs/milestones/M11-debugger-workbench.md`](../milestones/M11-debugger-workbench.md)  
**Design + adversarial review:** [`docs/design/EPIC-702-variable-editor.md`](../design/EPIC-702-variable-editor.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `a776cbea18050b15ae7cfd0d8dbd288f2f40aab7` | Squash merge of feature PR [#748](https://github.com/superche/openmatlab/pull/748) |
| Evidence merge tip | `e967ab7c7c34ce09b3f4380e87799726957c06fc` | Squash merge of [#749](https://github.com/superche/openmatlab/pull/749); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M11 criterion D09 is **met**. Epic #702 stays **open** until the user accepts it.

D09 is met on the headless Workbench model (`wb.variable_editor`): numeric, char, cell, scalar struct and table variables open as grids and a cell edit writes back with MATLAB indexed-assignment semantics. The tk Variables tab (double-click a Workspace row, double-click a cell) drives the same model.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| D09 variable editor open/edit/write-back | #702 | [#748](https://github.com/superche/openmatlab/pull/748) | [job 116828936682](https://github.com/superche/openmatlab/actions/runs/38856467146/job/116828936682) **success** |
| residual | #747 | [#748](https://github.com/superche/openmatlab/pull/748) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "A = [1 2; 3 4]; A(2,1) = 30; A"
A =

    1    2
   30    4
$ openmatlab -e "T = table([1;2],[3;4]); T{1,2} = 33; T"
T =

  2×2 table

    Var1    Var2
    ____    ____

       1      33
       2       4
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1750 passed, 2 deselected, 2 xfailed in 19.64s
$ pytest tests/unit/test_variable_editor.py tests/bdd/test_variable_editor_bdd.py "tests/conformance/test_m11_conformance.py::test_m11_criterion[D09-m11_d09_variable_editor]" --tb=no
14 passed in 0.44s
$ pytest tests/conformance/test_m11_conformance.py --tb=no
10 passed, 1 xfailed in 0.47s
```

New cases: `tests/unit/test_variable_editor.py` (11), `tests/bdd/test_variable_editor_bdd.py` (2), M11 D09 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F host.variable_editor
host.variable_editor             host       done     Variable editor panel
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Struct-array/object editing, insert/delete rows, paste, plot from selection, nested open | [#747](https://github.com/superche/openmatlab/issues/747) |

## Milestone progress (M11)

- Criteria met: **9 / 10** (D01, D02, D03, D04, D05, D06, D07, D08, D09)
- Conformance scripts passing: **9 / 10** (strict xfail pending: D10)
- Next: D-E6 #703 Workbench workflows, then T-E7 #697.
