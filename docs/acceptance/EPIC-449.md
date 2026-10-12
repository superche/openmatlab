# Acceptance evidence — Epic #449 (complex numbers)

**Epic:** [#449 Epic: complex numbers](https://github.com/superche/openmatlab/issues/449)  
**Scope issues (closed by PR #450):** [#71](https://github.com/superche/openmatlab/issues/71) · [#229](https://github.com/superche/openmatlab/issues/229) (complex half; sparse → #451). Also unblocks [#228](https://github.com/superche/openmatlab/issues/228)'s deferred complex results (#228 itself was closed earlier by #434).  
**Milestone:** [Octave-breadth language & numerics (M2)](https://github.com/superche/openmatlab/milestone/2) · [`docs/milestones/M2-octave-breadth.md`](../milestones/M2-octave-breadth.md)  
**Design + adversarial review:** [`docs/design/EPIC-449-complex.md`](../design/EPIC-449-complex.md)  
**Captured:** 2026-10-12 ~22:23 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `0aea57e5f103d48d812f475a1df1cd6b6d311301` | Squash merge of [#450](https://github.com/superche/openmatlab/pull/450) |
| Evidence merge tip | `3be4ff53d8625e93c66c19c68e11a73eae478e4b` | Squash merge of [#455](https://github.com/superche/openmatlab/pull/455); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** #71 and #229 are closed. M2 criterion C13 is **met**. The epic issue #449 stays **open** until the user accepts it.

## Traceability — Issues → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| literals, arithmetic, elfun, parts, compare, reductions, sort, display | #71 | [#450](https://github.com/superche/openmatlab/pull/450) | [job 114855636358](https://github.com/superche/openmatlab/actions/runs/38262305562/job/114855636358) **success** |
| complex matrix power | #229 | #450 | same |
| fractional / negative-base power results (deferred in #434) | #228 | #450 | same |

## Functional demo (real CLI output)

```text
$ openmatlab -e "z = (3+4i)*(1-2i)"
z =

11 - 2i

$ openmatlab -e "s = sqrt(-4), l = log(-1)"
s =

0 + 2i

l =

0.0000 + 3.1416i

$ openmatlab -e "c = (-8)^(1/3)"
c =

1.0000 + 1.7321i

$ openmatlab -e "A = [1 2; 3 4]^0.5"
A =

   0.5537 + 0.4644i   0.8070 - 0.2124i
   1.2104 - 0.3186i   1.7641 + 0.1458i

$ openmatlab -e "z = [1+2i 3]'"
z =

   1 - 2i
   3 - 0i

$ openmatlab -e "m = max([1 -3i 2]), s = sort([3 1i -2])"
m =

0 - 3i

s =

    0 + 1i   -2 + 0i    3 + 0i

$ openmatlab -e "r = isreal(1i*1i), k = class(1i)"
r =

1

k =

double
```

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
693 passed, 2 deselected in 2.29s
$ pytest tests/conformance --tb=no
20 passed in 0.43s
$ pytest tests/unit/test_complex_numbers.py tests/bdd/test_complex_numbers_bdd.py "tests/conformance/test_m2_conformance.py::test_m2_criterion[C13-c13_complex]"
29 passed in 0.48s
```

New cases: 24 unit (`tests/unit/test_complex_numbers.py`), 4 Gherkin scenarios
(`features/complex_numbers.feature`), and conformance `c13_complex`.

### Existing tests changed (each asserted an error MATLAB does not raise)

1. `tests/unit/test_matrix_power_expm.py::test_complex_results_are_deferred_to_71`
   became `test_complex_results_now_supported_71`. It asserts `(-2)^[1 0;0 1]` = `[-2 0;0 -2]` and `[-1 0;0 1]^0.5` = `[1i 0;0 1]`.
2. `tests/unit/test_elfun.py::test_real_domain_errors` used to expect `sqrt(-1)` and `log([1 -2])` to raise.
   It now asserts `1i` and `[0, log(2)+pi*i]`. The `mod` dimension-error assertion is unchanged.
3. `tests/unit/test_elfun.py::test_builtin_error_message_not_duplicated` used `sqrt(-1)` only as an erroring call,
   and that call is now valid. The vehicle is now `sqrt(1, 2)` (an arity error). The assertion is unchanged.

## Feature map (epic-related)

```text
$ openmatlab features --layer numerics | rg complex
numerics.complex                 numerics   partial  complex numbers: literals, arithmetic, elfun, power, display
```

`libs.elfun` notes were updated: negative sqrt/log now go to the complex domain. `numerics.complex` stays `partial` because of the residuals below.

## Milestone progress (M2)

- Criteria met: **13 / 13** (C13 complex added at p2 and met by this epic)
- Conformance scripts passing: **13 / 13** (xfail pending: none)
- Remaining gaps (priority order): integer/string classes #72 #78 #183 (next epic) · N-D residuals #442–#446 · complex residuals #451–#454

## Residuals (filed, same milestone)

| Issue | Residual |
|-------|----------|
| [#451](https://github.com/superche/openmatlab/issues/451) | sparse matrices (incl. sparse matrix power; sparse half of #229) |
| [#452](https://github.com/superche/openmatlab/issues/452) | complex `unique` / `issorted` |
| [#453](https://github.com/superche/openmatlab/issues/453) | scaled / large-magnitude complex display |
| [#454](https://github.com/superche/openmatlab/issues/454) | complex elfun parity coverage (trig, branch cuts) |
