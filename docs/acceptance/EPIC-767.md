# Acceptance evidence: Epic #767 (G-E0 Workbench output routing (#760))

**Epic:** [#767](https://github.com/superche/openmatlab/issues/767)  
**Feature PR:** [#777](https://github.com/superche/openmatlab/pull/777) (#760, #767, #776)  
**Milestone:** [Graphics completion (M13)](https://github.com/superche/openmatlab/milestone/13) · [`docs/milestones/M13-graphics.md`](../milestones/M13-graphics.md)  
**Design + adversarial review:** [`docs/design/EPIC-767-output-routing.md`](../design/EPIC-767-output-routing.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `fdbb1881004682bc43b9958af75ccdc66d099bfd` | Squash merge of feature PR [#777](https://github.com/superche/openmatlab/pull/777) |
| Evidence merge tip | `a4cf6651070111eece0de054f488e7c9b85b7322` | Squash merge of [#778](https://github.com/superche/openmatlab/pull/778); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M13 criterion G09 is **partially met**: the output-routing half (#760) is delivered; G09 stays strict-xfail pending until G-E7 #774 adds figure docking and focus. Epic #767 stays **open** until the user accepts it.

Script, function and builtin writes to stdout/stderr (`fprintf` fid 1/2, `disp`, `warning`, `toc`, `whos`, table display) now land in the Command Window of the evaluating thread, in order with value display and error text. Other threads and other Workbenches are unaffected, and `evalc` still captures.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| fprintf/disp output goes to the Command Window | #760 | [#777](https://github.com/superche/openmatlab/pull/777) | [job 116968199712](https://github.com/superche/openmatlab/actions/runs/38899575407/job/116968199712) **success** |
| G-E0 epic | #767 | [#777](https://github.com/superche/openmatlab/pull/777) | same job |
| residual | #776 | [#777](https://github.com/superche/openmatlab/pull/777) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "fprintf('total = %d\n', 7); disp('hello')"
total = 7
hello
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1796 passed, 2 deselected, 20 xfailed in 21.18s
$ pytest tests/unit/test_workbench_output_routing.py tests/bdd/test_workbench_output_routing_bdd.py "tests/conformance/test_m13_conformance.py::test_m13_criterion[G09-m13_g09_workbench_figures]" --tb=no
9 passed, 1 xfailed in 0.43s
$ pytest tests/conformance/test_m13_conformance.py --tb=no
1 passed, 10 xfailed in 0.61s
```

New cases: `tests/unit/test_workbench_output_routing.py` (7), `tests/bdd/test_workbench_output_routing_bdd.py` (2). G09 conformance stays strict xfail (docking pending).

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F host.workbench.output_routing
host.workbench.output_routing    host       done     Workbench output routing to the Command Window
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| stderr text not coloured red in the tk Command Window | [#776](https://github.com/superche/openmatlab/issues/776) |

## Milestone progress (M13)

- Criteria met: **0 / 10** (none yet; G09 half delivered)
- Conformance scripts passing: **0 / 10** (strict xfail pending: G01, G02, G03, G04, G05, G06, G07, G08, G09, G10)
- Next: M12 C-E1 #761 corpus runner.
