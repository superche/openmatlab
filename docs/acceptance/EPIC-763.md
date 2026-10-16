# Acceptance evidence: Epic #763 (C-E3 corpus preprocessing and failure classifier)

**Epic:** [#763](https://github.com/superche/openmatlab/issues/763)  
**Feature PR:** [#790](https://github.com/superche/openmatlab/pull/790) (#763, #789)  
**Milestone:** [Real-script compatibility gate (M12)](https://github.com/superche/openmatlab/milestone/12) · [`docs/milestones/M12-corpus-gate.md`](../milestones/M12-corpus-gate.md)  
**Design + adversarial review:** [`docs/design/EPIC-763-preprocess-classifier.md`](../design/EPIC-763-preprocess-classifier.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `b66655897ceadb91136dd0de9dc7c472a1dfabb3` | Squash merge of feature PR [#790](https://github.com/superche/openmatlab/pull/790) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M12 criterion C03 is **met**. Epic #763 stays **open** until the user accepts it.

Deterministic preprocessing (de-prompting, echo stripping, function-file detection, `input` fixtures, fragment detection) cuts residual noise on the Rosetta script set to 5.5 % (raw 43.8 %), which meets C03. The rule-based classifier (internal-crash, timeout, corpus-noise, toolbox, io-env, graphics, missing-builtin, parse-error, semantics-diff) scores 92.0 % on 88 hand-labelled failures with 100 % crash recall, which meets C04 (conformance `m12_c04_classifier` is also met).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| C03 preprocessing, C04 classifier | #763 | [#790](https://github.com/superche/openmatlab/pull/790) | [job 117007439187](https://github.com/superche/openmatlab/actions/runs/38911272493/job/117007439187) **success** |
| residual: labelled-set misses, fragment blind spots | #789 | [#790](https://github.com/superche/openmatlab/pull/790) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "disp('corpus: see python -m openmatlab.qa.corpus run')"
corpus: see python -m openmatlab.qa.corpus run
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1860 passed, 2 deselected, 16 xfailed in 56.23s
$ pytest tests/unit/test_corpus_preprocess_classify.py tests/bdd/test_corpus_classifier_bdd.py "tests/conformance/test_m12_conformance.py::test_m12_criterion[C03-m12_c03_preprocess]" --tb=no
35 passed in 2.34s
$ pytest tests/conformance/test_m12_conformance.py --tb=no
5 passed, 6 xfailed in 3.60s
```

New cases: `tests/unit/test_corpus_preprocess_classify.py`, `tests/bdd/test_corpus_classifier_bdd.py`; M12 C03 and C04 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F qa.corpus_classifier
qa.corpus_classifier             qa         done     Corpus root-cause classifier and labelled set
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| 7 labelled misses, fragment detector blind spots | [#789](https://github.com/superche/openmatlab/issues/789) |

## Milestone progress (M12)

- Criteria met: **4 / 10** (C01, C02, C03, C04)
- Conformance scripts passing: **4 / 10** (strict xfail pending: C05, C06, C07, C08, C09, C10)
- Next: C-E4 #764 report, dashboard, regression gate and corpus issue filing.
