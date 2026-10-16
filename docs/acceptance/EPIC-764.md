# Acceptance evidence: Epic #764 (C-E4 corpus REPORT dashboard, regression gate, deduplicated corpus issues)

**Epic:** [#764](https://github.com/superche/openmatlab/issues/764)  
**Feature PR:** [#834](https://github.com/superche/openmatlab/pull/834) (#764, #832, #833)  
**Milestone:** [Real-script compatibility gate (M12)](https://github.com/superche/openmatlab/milestone/12) · [`docs/milestones/M12-corpus-gate.md`](../milestones/M12-corpus-gate.md)  
**Design + adversarial review:** [`docs/design/EPIC-764-report-triage.md`](../design/EPIC-764-report-triage.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `907d8ca4178b53999372c60e08211d050ddc6e9e` | Squash merge of feature PR [#834](https://github.com/superche/openmatlab/pull/834) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M12 criterion C10 is **met**. Epic #764 stays **open** until the user accepts it.

`python -m openmatlab.qa.corpus report` generates `docs/corpus/REPORT.md` (first full run: T0 87.5 % (850/971), T1 26.1 % (184/706), T2/T3 no oracle yet). `gate` exits 1 on any pass->fail regression against the committed results. `triage --file` filed 39 failure groups as deduplicated `corpus` issues (#793-#831); a re-run reports all 39 as already filed. Thresholds are calibrated and locked in the M12 doc: T0 95 %, T1 65 %, T2 75 %, T3 70 %. The CI workflow (nightly full run, PR sample) is staged at `docs/corpus/ci/corpus.yml` because the agent token lacks the workflow scope (#833).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| C10 report, gate, triage | #764 | [#834](https://github.com/superche/openmatlab/pull/834) | [job 117016537921](https://github.com/superche/openmatlab/actions/runs/38913959835/job/117016537921) **success** |
| residual: timeout flake, Octave T0, closed-group refile | #832 | [#834](https://github.com/superche/openmatlab/pull/834) | same job |
| residual: install corpus workflow | #833 | [#834](https://github.com/superche/openmatlab/pull/834) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "disp('corpus: see python -m openmatlab.qa.corpus report')"
corpus: see python -m openmatlab.qa.corpus report
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1873 passed, 2 deselected, 15 xfailed in 55.99s
$ pytest tests/unit/test_corpus_report_triage.py tests/bdd/test_corpus_report_bdd.py "tests/conformance/test_m12_conformance.py::test_m12_criterion[C10-m12_c10_report_triage]" --tb=no
12 passed in 0.20s
$ pytest tests/conformance/test_m12_conformance.py --tb=no
6 passed, 5 xfailed in 3.60s
```

New cases: `tests/unit/test_corpus_report_triage.py` (10), `tests/bdd/test_corpus_report_bdd.py` (2); M12 C10 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F qa.corpus_report
qa.corpus_report                 qa         done     Corpus REPORT dashboard, regression gate, deduplicated corpus issue filing
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Gate timeout flakiness, Octave T0 not measured, closed groups not refiled | [#832](https://github.com/superche/openmatlab/issues/832) |
| Install corpus CI workflow (workflow scope) | [#833](https://github.com/superche/openmatlab/issues/833) |

## Milestone progress (M12)

- Criteria met: **5 / 10** (C01, C02, C03, C04, C10)
- Conformance scripts passing: **5 / 10** (strict xfail pending: C05, C06, C07, C08, C09)
- Next: C-E6 #766 burn-down (C05, C06, C09), interleaved with M13 epics ranked by corpus graphics failures.
