# Acceptance evidence: Epic #626 (polynomials and interpolation)

**Epic:** [#626](https://github.com/superche/openmatlab/issues/626)  
**Feature PR:** [#650](https://github.com/superche/openmatlab/pull/650) (#626)  
**Milestone:** [Domain toolboxes (M3)](https://github.com/superche/openmatlab/milestone/3) · [`docs/milestones/M3-domain-toolboxes.md`](../milestones/M3-domain-toolboxes.md)  
**Design + adversarial review:** [`docs/design/EPIC-626-poly-interp.md`](../design/EPIC-626-poly-interp.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `95a9742f02e4735436701548f3b2354ee843db89` | Squash merge of feature PR [#650](https://github.com/superche/openmatlab/pull/650) |
| Evidence merge tip | `304954ed950280bc8565812a43fc3aaa7dac4bde` | Squash merge of [#651](https://github.com/superche/openmatlab/pull/651); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M3 criterion T02 is **met**. Epic #626 stays **open** until the user accepts it.

Covered:
- `spline`, not-a-knot and clamped;
- `pchip`, Fritsch–Carlson;
- pp structs with `ppval`/`mkpp`/`unmkpp`;
- `interp1` 'spline'/'pchip'/'cubic', extrapolating by default;
- `interp2` linear/nearest, with NaN or an extrapval outside the grid;
- `polyder`, including product and quotient forms;
- `polyint` with a constant;
- `poly`.

T02 is met.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| M3-E2 polynomials and interpolation (T02) | #626 | [#650](https://github.com/superche/openmatlab/pull/650) | [job 115202630685](https://github.com/superche/openmatlab/actions/runs/38369489991/job/115202630685) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "spline(0:3, (0:3).^3, 1.5)"
ans =

3.3750
$ openmatlab -e "pp = spline(0:3, (0:3).^3); ppval(pp, 2.5)"
ans =

15.6250
$ openmatlab -e "pchip(1:6, [1 1 1 2 2 2], 3.5)"
ans =

1.5000
$ openmatlab -e "[X, Y] = meshgrid(1:3, 1:2); interp2(X, Y, X + 10*Y, 2.5, 1.5)"
ans =

17.5000
$ openmatlab -e "[q, d] = polyder([1 0], [1 1])"
q =

1

d =

   1   2   1
$ openmatlab -e "polyint([3 2 1], 5)"
ans =

   1   1   1   5
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1411 passed, 2 deselected, 11 xfailed in 19.05s
$ pytest tests/unit/test_interp_poly.py tests/bdd/test_interp_poly_bdd.py "tests/conformance/test_m3_conformance.py::test_m3_criterion[T02-m3_t02_poly_interp]" --tb=no
10 passed in 0.47s
$ pytest tests/conformance/test_m3_conformance.py --tb=no
3 passed, 5 xfailed in 0.46s
```

New cases: 7 unit tests (`tests/unit/test_interp_poly.py`), 2 Gherkin scenarios (`features/interp_poly.feature`), and conformance `m3_t02_poly_interp` (18 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F numerics.interp_poly
numerics.interp_poly             numerics   done     splines, pchip, ppval, interp1 spline/pchip, interp2, polyder, polyint
```

## Residuals (filed)

- [#649](https://github.com/superche/openmatlab/issues/649) (p2): vector-valued splines, `interp2` cubic/spline, `makima`, `interp1` with matrix Y.

## Milestone progress (M3)

- Criteria met: **2 / 7** (T01, T02)
- Conformance scripts passing: **2 / 7** (strict xfail pending: T03, T04, T05, T06, T07)
- Next: O-E4 operators/indexing/display (#621), then M3-E3 (#627)
