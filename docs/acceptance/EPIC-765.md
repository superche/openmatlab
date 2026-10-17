# Acceptance evidence: Epic #765 (C-E5 T2 self-check oracle; T3 pending)

**Epic:** [#765](https://github.com/superche/openmatlab/issues/765)  
**Feature PRs:** #900-#911 (harness and burn-downs); [#913](https://github.com/superche/openmatlab/pull/913) (C07 met, full run) (#765)  
**Milestone:** [Real-script compatibility gate (M12)](https://github.com/superche/openmatlab/milestone/12) · [`docs/milestones/M12-corpus-gate.md`](../milestones/M12-corpus-gate.md)  
**Design + adversarial review:** [`docs/design/EPIC-765-oracles.md`](../design/EPIC-765-oracles.md)  
**Captured:** 2026-10-17 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `78c44ef8fc1e26211fba4db4644c88776e42d3d0` | Squash merge of the C07 full-run PR [#913](https://github.com/superche/openmatlab/pull/913) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M12 criterion C07 (T2 self-check) is **met** for the T2 part; C08 (T3 goldens) is **pending Shaw's decision on golden sourcing** and no T3 oracle is built. Epic #765 stays **open** until the user accepts it.

The T2 oracle runs GNU Octave `%!assert`/`%!test` blocks at run time against OpenMATLAB's own functions (pass/fail, hashes, counts and redacted messages only; no Octave test source or expected values are committed), plus chebfun's and matlab2tikz's own checks. Full run on `20145ad` (tree-identical to `main` `2104b1c`): **T2 82.3 % (3426/4161)** against the locked 75 % threshold, T0 99.5 % (966/971), T1 68.0 % (458/674), internal-crash 0, no pass->fail regression against the `b23f9b7` baseline. 128 dialect-excluded Octave blocks (`corpus/dialect.json`, documented MATLAB behaviour differs) are outside the rate and never a pass; counted as failures, T2 would be 79.9 %. Progression: 64.1 % (#904) -> 71.7 % (#909) -> 82.3 % (#913). **C08 (T3) is not met** and waits for Shaw's golden-sourcing decision, so #765 stays open either way.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| T2 self-check harness (Octave `%!` blocks at run time, chebfun/matlab2tikz own checks) | #765 | [#900](https://github.com/superche/openmatlab/pull/900) | [job 117281896097](https://github.com/superche/openmatlab/actions/runs/38993857405/job/117281896097) **success** |
| T2 burn-down 1 | #765 | [#901](https://github.com/superche/openmatlab/pull/901) | [job 117284239883](https://github.com/superche/openmatlab/actions/runs/38994596670/job/117284239883) **success** |
| T2 burn-down 2 | #765 | [#902](https://github.com/superche/openmatlab/pull/902) | [job 117288423781](https://github.com/superche/openmatlab/actions/runs/38995946582/job/117288423781) **success** |
| T2 burn-down 3 | #765 | [#903](https://github.com/superche/openmatlab/pull/903) | [job 117290935997](https://github.com/superche/openmatlab/actions/runs/38996765953/job/117290935997) **success** |
| first full T2 run (64.1 %) | #765 | [#904](https://github.com/superche/openmatlab/pull/904) | [job 117293600917](https://github.com/superche/openmatlab/actions/runs/38997644152/job/117293600917) **success** |
| T2 burn-down 4 | #765 | [#905](https://github.com/superche/openmatlab/pull/905) | [job 117294680976](https://github.com/superche/openmatlab/actions/runs/38997993004/job/117294680976) **success** |
| T2 burn-down 5 | #765 | [#906](https://github.com/superche/openmatlab/pull/906) | [job 117295174967](https://github.com/superche/openmatlab/actions/runs/38998154174/job/117295174967) **success** |
| T2 burn-down 6 | #765 | [#907](https://github.com/superche/openmatlab/pull/907) | [job 117295935152](https://github.com/superche/openmatlab/actions/runs/38998401949/job/117295935152) **success** |
| T2 burn-down 7 | #765 | [#908](https://github.com/superche/openmatlab/pull/908) | [job 117296790174](https://github.com/superche/openmatlab/actions/runs/38998684301/job/117296790174) **success** |
| full T2 run (71.7 %), `mean` overflow fix | #765 | [#909](https://github.com/superche/openmatlab/pull/909) | [job 117306994565](https://github.com/superche/openmatlab/actions/runs/39002095264/job/117306994565) **success** |
| quadrature engine, dialect exclusions | #765 | [#910](https://github.com/superche/openmatlab/pull/910) | [job 117308133075](https://github.com/superche/openmatlab/actions/runs/39002478152/job/117308133075) **success** |
| `funm`/`logm`, moving statistics, `trapz`, `strsplit` | #765 | [#911](https://github.com/superche/openmatlab/pull/911) | [job 117310926024](https://github.com/superche/openmatlab/actions/runs/39003428065/job/117310926024) **success** |
| C07 met: full T2 run (82.3 %) | #765 | [#913](https://github.com/superche/openmatlab/pull/913) | [job 117314447019](https://github.com/superche/openmatlab/actions/runs/39004621619/job/117314447019) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "disp(abs(quadgk(@(x) exp(-x.^2), -Inf, Inf)^2 - pi) < 1e-10); A = [1 2; 0 3]; disp(norm(funm(A, @exp) - expm(A)) < 1e-10); disp(interp1([1 2 3], [4 5 6], 4, 'pchip')); disp(trapz([1 2 3]))"
1
1
7
4
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
2152 passed, 14 deselected, 5 xfailed in 79.36s (0:01:19)
$ pytest tests/unit/test_corpus_selfcheck.py tests/unit/test_t2_builtins.py tests/unit/test_t2_integrate_split.py tests/unit/test_t2_matfun.py tests/unit/test_t2_moving.py "tests/conformance/test_m12_conformance.py::test_m12_criterion[C07-m12_c07_tier2]" --tb=no
81 passed in 0.82s
$ pytest tests/conformance/test_m12_conformance.py --tb=no
10 passed, 1 xfailed in 3.65s
```

New cases: `tests/unit/test_corpus_selfcheck.py` (harness, block splitting, Octave normalisation, dialect exclusions) and `tests/unit/test_t2_*.py` (burn-down builtins), added across #900-#911; C07 conformance flipped to met in #913.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F qa.corpus_tier2
qa.corpus_tier2                  qa         done     Corpus T2 self-check oracle and dialect exclusions
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| C08 T3 golden oracle: golden sourcing awaits Shaw's decision | #765 (stays open) |
| T2 long tail (`assert-mismatch`, undefined functions, ...) | deduplicated `corpus` issues; #766 burn-down |
| Interpreter timeouts (52 entries) | #797 |

## Milestone progress (M12)

- Criteria met: **9 / 10** (C01-C07, C09, C10)
- Conformance scripts passing: **9 / 10** (strict xfail pending: C08, waiting on Shaw's golden-sourcing decision)
- Next: C08 (T3) once Shaw decides golden sourcing; M13 G-E4 #771, G-E6 #773, G-E7 #774; cheap #766/#797 burn-down.
