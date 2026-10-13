# Acceptance evidence: Epic #534 (core math, statistics, random numbers, timing)

**Epic:** [#534](https://github.com/superche/openmatlab/issues/534)  
**Feature PR:** [#582](https://github.com/superche/openmatlab/pull/582) (#550, #551, #552)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-534-core-math.md`](../design/EPIC-534-core-math.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `043d65eeb866deb3f52fea1358476f02f50a4de6` | Squash merge of feature PR [#582](https://github.com/superche/openmatlab/pull/582) |
| Evidence merge tip | `785ac1e6899b2d038c88cca1495a29f5f2361cc7` | Squash merge of [#583](https://github.com/superche/openmatlab/pull/583); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M7 criterion C05 is **met**. Epic #534 stays **open** until the user accepts it.

Covered:
- number theory and difference/cumulative ops;
- statistics with MATLAB's dimension, weight and NaN rules;
- `rng`/`rand`: the stream is bit-identical to MATLAB's default twister (`rng(0); rand` gives 0.8147…);
- `randn`/`randi`/`randperm` and `tic`/`toc`/`pause`;
- the everyday numeric helpers: `isnan` family, degree trig, polynomials, `filter`, `interp1`, `histcounts`/`accumarray`, `fzero`/`fminsearch`/`integral`.

Integer classes saturate.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| fix rem sign hypot log2 diff cumprod gcd lcm primes factor isprime nchoosek factorial round(x,n) | #550 | [#582](https://github.com/superche/openmatlab/pull/582) | [job 115142282230](https://github.com/superche/openmatlab/actions/runs/38350729376/job/115142282230) **success** |
| median mode std var (dims, weights, omitnan), cov corrcoef range bounds | #551 | [#582](https://github.com/superche/openmatlab/pull/582) | same job |
| rng rand randn randi randperm tic toc pause | #552 | [#582](https://github.com/superche/openmatlab/pull/582) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "rng(0); r = rand(2)"
r =

   0.8147   0.1270
   0.9058   0.9134
$ openmatlab -e "[f, e] = log2(8), p = primes(20), k = nchoosek(5, 2)"
f =

0.5000

e =

4

p =

    2    3    5    7   11   13   17   19

k =

10
$ openmatlab -e "s = std([2 4 4 4 5 5 7 9]), m = median([1 2; 3 4])"
s =

2.1381

m =

   2   3
$ openmatlab -e "x = fzero(@(x) cos(x) - x, [0 1]), q = integral(@(x) exp(-x.^2), -Inf, Inf)"
x =

0.7391

q =

1.7725
$ openmatlab -e "tic; pause(0.05); t = toc; ok = t > 0.04"
ok =

1
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1240 passed, 2 deselected, 5 xfailed in 15.43s
$ pytest tests/unit/test_core_math.py tests/bdd/test_core_math_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C05-m7_c05_core_math]" --tb=no
27 passed in 0.57s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
6 passed, 5 xfailed in 0.50s
```

New cases: 21 unit tests (`tests/unit/test_core_math.py`), 5 Gherkin scenarios (`features/core_math.feature`), and conformance `m7_c05_core_math` (37 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.core_math
libs.core_math                   libs       done     core math, statistics, random numbers, timing
```

## Residuals (filed)

- [#581](https://github.com/superche/openmatlab/issues/581) (p2): randn/randi stream parity, prctile/quantile, interp1 spline/matrix Y, solver options, histc.

## Milestone progress (M7)

- Criteria met: **5 / 10** (C01–C05)
- Conformance scripts passing: **5 / 10** (strict xfail pending: C06–C10)
- Next: Epic #535 (C06 arrays & sets)
