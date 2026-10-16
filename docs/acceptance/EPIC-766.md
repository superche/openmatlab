# Acceptance evidence: Epic #766 (C-E6 corpus burn-down (rolling): internal crash = 0)

**Epic:** [#766](https://github.com/superche/openmatlab/issues/766)  
**Feature PR:** [#839](https://github.com/superche/openmatlab/pull/839) (#766, #838)  
**Milestone:** [Real-script compatibility gate (M12)](https://github.com/superche/openmatlab/milestone/12) · [`docs/milestones/M12-corpus-gate.md`](../milestones/M12-corpus-gate.md)  
**Design + adversarial review:** [`docs/design/EPIC-766-burn-down.md`](../design/EPIC-766-burn-down.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `52ad61bcd7ed5c40aca78a1e92583eb0d1f2a84c` | Squash merge of feature PR [#839](https://github.com/superche/openmatlab/pull/839) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M12 criterion C09 is **met**; C05 and C06 remain pending (rolling burn-down continues). Epic #766 stays **open** until the user accepts it.

The full corpus re-run reports `internal-crash` = 0 (was 2): `*` width/precision in `sprintf`/`fprintf` and `display` inside function bodies no longer raise Python errors. Pass rates: T0 87.5 % (850/971), T1 26.2 % (185/706). C-E6 is rolling: C05 (T0 ≥ 95 %) and C06 (T1 ≥ 65 %) continue in later increments.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| C09 internal crash = 0 | #766 | [#839](https://github.com/superche/openmatlab/pull/839) | [job 117029217602](https://github.com/superche/openmatlab/actions/runs/38917669492/job/117029217602) **success** |
| residual: display in function bodies | #838 | [#839](https://github.com/superche/openmatlab/pull/839) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "fprintf('%*d|\n', 5, 42)"
   42|
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1879 passed, 2 deselected, 14 xfailed in 56.80s
$ pytest tests/unit/test_corpus_crash_fixes.py "tests/conformance/test_m12_conformance.py::test_m12_criterion[C09-m12_c09_no_crash]" --tb=no
5 passed in 0.44s
$ pytest tests/conformance/test_m12_conformance.py --tb=no
7 passed, 4 xfailed in 3.61s
```

New cases: `tests/unit/test_corpus_crash_fixes.py`; M12 C09 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F qa.corpus_no_crash
qa.corpus_no_crash               qa         done     Corpus full run has no internal crash (sprintf star width, display in functions)
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Unsuppressed statements in function bodies print nothing | [#838](https://github.com/superche/openmatlab/issues/838) |

## Milestone progress (M12)

- Criteria met: **6 / 10** (C01, C02, C03, C04, C09, C10)
- Conformance scripts passing: **6 / 10** (strict xfail pending: C05, C06, C07, C08)
- Next: #766 burn-down of top corpus issues by T1 impact (C05, C06), C-E5 #765 (C07, C08), M13 epics.
