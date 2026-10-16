# Acceptance evidence: Epic #762 (C-E2 corpus manifest, runtime fetch, licence allow-list)

**Epic:** [#762](https://github.com/superche/openmatlab/issues/762)  
**Feature PR:** [#786](https://github.com/superche/openmatlab/pull/786) (#762, #785)  
**Milestone:** [Real-script compatibility gate (M12)](https://github.com/superche/openmatlab/milestone/12) · [`docs/milestones/M12-corpus-gate.md`](../milestones/M12-corpus-gate.md)  
**Design + adversarial review:** [`docs/design/EPIC-762-corpus-manifest.md`](../design/EPIC-762-corpus-manifest.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `a972b09264471fe3d7e352fd99918b7ce6ee9797` | Squash merge of feature PR [#786](https://github.com/superche/openmatlab/pull/786) |
| Evidence merge tip | `8a724edcbdf7ca2e7ea1477726da32ca62efa071` | Squash merge of [#787](https://github.com/superche/openmatlab/pull/787); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M12 criterion C01 is **met**. Epic #762 stays **open** until the user accepts it.

`corpus/manifest.json` lists 1495 entries (1233 runnable) from Rosetta Code (GFDL, runtime only), GNU Octave (GPL, runtime only), chebfun (BSD-3) and matlab2tikz (BSD-2), each with URL, revid/commit and sha256. `python -m openmatlab.qa.corpus fetch` restores the cache at the pins and verifies hashes; `check` (also run by C01 in CI) enforces the licence allow-list and finds no copyleft bodies in the repo.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| C01 corpus manifest | #762 | [#786](https://github.com/superche/openmatlab/pull/786) | [job 116980923131](https://github.com/superche/openmatlab/actions/runs/38903403342/job/116980923131) **success** |
| residual: partial-copy scan | #785 | [#786](https://github.com/superche/openmatlab/pull/786) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "disp('corpus: see python -m openmatlab.qa.corpus check')"
corpus: see python -m openmatlab.qa.corpus check
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1823 passed, 2 deselected, 18 xfailed in 54.54s
$ pytest tests/unit/test_corpus_manifest.py tests/bdd/test_corpus_manifest_bdd.py "tests/conformance/test_m12_conformance.py::test_m12_criterion[C01-m12_c01_corpus_manifest]" --tb=no
11 passed in 0.55s
$ pytest tests/conformance/test_m12_conformance.py --tb=no
3 passed, 8 xfailed in 3.49s
```

New cases: `tests/unit/test_corpus_manifest.py` (8), `tests/bdd/test_corpus_manifest_bdd.py` (2), M12 C01 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F qa.corpus_manifest
qa.corpus_manifest               qa         done     Corpus manifest, runtime fetch and licence allow-list
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Copyleft scan detects whole-file copies only | [#785](https://github.com/superche/openmatlab/issues/785) |

## Milestone progress (M12)

- Criteria met: **2 / 10** (C01, C02)
- Conformance scripts passing: **2 / 10** (strict xfail pending: C03, C04, C05, C06, C07, C08, C09, C10)
- Next: C-E3 #763 preprocessing and classifier.
