# Acceptance evidence: Epic #761 (C-E1 sandboxed corpus runner)

**Epic:** [#761](https://github.com/superche/openmatlab/issues/761)  
**Feature PR:** [#782](https://github.com/superche/openmatlab/pull/782) (#761, #780, #781)  
**Milestone:** [Real-script compatibility gate (M12)](https://github.com/superche/openmatlab/milestone/12) · [`docs/milestones/M12-corpus-gate.md`](../milestones/M12-corpus-gate.md)  
**Design + adversarial review:** [`docs/design/EPIC-761-corpus-runner.md`](../design/EPIC-761-corpus-runner.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `ffea4e4efd056b16272a59c9bff3383dc722b3d8` | Squash merge of feature PR [#782](https://github.com/superche/openmatlab/pull/782) |
| Evidence merge tip | `ee493543baf4fa898f1d78b34be12b4f8f9af152` | Squash merge of [#783](https://github.com/superche/openmatlab/pull/783); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M12 criterion C02 is **met**. Epic #761 stays **open** until the user accepts it.

`openmatlab run FILE --timeout S --json` and `openmatlab.qa.corpus.runner.run_many` run each script in its own sandboxed child (fresh workdir/HOME, stdin closed, rlimits, process-group kill). A hang, flood, crash or forged output in one script never changes another's result. 50 pilot scripts ran in 13.3 s on 8 CPUs.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| C02 runner isolation | #761 | [#782](https://github.com/superche/openmatlab/pull/782) | [job 116973502158](https://github.com/superche/openmatlab/actions/runs/38901168323/job/116973502158) **success** |
| residual: OS-level network isolation | #780 | [#782](https://github.com/superche/openmatlab/pull/782) | same job |
| residual: MemoryError/RecursionError as MATLAB errors | #781 | [#782](https://github.com/superche/openmatlab/pull/782) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "disp(1+1)"
2
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1811 passed, 2 deselected, 19 xfailed in 54.66s
$ pytest tests/unit/test_corpus_runner.py tests/bdd/test_corpus_runner_bdd.py "tests/conformance/test_m12_conformance.py::test_m12_criterion[C02-m12_c02_runner_isolation]" --tb=no
14 passed in 31.74s
$ pytest tests/conformance/test_m12_conformance.py --tb=no
2 passed, 9 xfailed in 3.25s
```

New cases: `tests/unit/test_corpus_runner.py` (11), `tests/bdd/test_corpus_runner_bdd.py` (2), M12 C02 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F qa.corpus_runner
qa.corpus_runner                 qa         done     Sandboxed corpus runner (openmatlab run)
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Network isolation at OS level (unshare/netns) | [#780](https://github.com/superche/openmatlab/issues/780) |
| Out-of-memory / deep recursion surface as internal errors | [#781](https://github.com/superche/openmatlab/issues/781) |

## Milestone progress (M12)

- Criteria met: **1 / 10** (C02)
- Conformance scripts passing: **1 / 10** (strict xfail pending: C01, C03, C04, C05, C06, C07, C08, C09, C10)
- Next: C-E2 #762 corpus fetch, manifest and licence allow-list.
