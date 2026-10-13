# Acceptance evidence: Epic #627 (ODE solvers, quadrature and optimisation with options)

**Epic:** [#627](https://github.com/superche/openmatlab/issues/627)  
**Feature PR:** [#658](https://github.com/superche/openmatlab/pull/658) (#627)  
**Milestone:** [Domain toolboxes (M3)](https://github.com/superche/openmatlab/milestone/3) · [`docs/milestones/M3-domain-toolboxes.md`](../milestones/M3-domain-toolboxes.md)  
**Design + adversarial review:** [`docs/design/EPIC-627-ode-quad-opt.md`](../design/EPIC-627-ode-quad-opt.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `d31f7778cca69ae5271f9a73cc7ed72ad4b94851` | Squash merge of feature PR [#658](https://github.com/superche/openmatlab/pull/658) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M3 criterion T03 is **met**. Epic #627 stays **open** until the user accepts it.

Covered:
- `ode45` (Dormand–Prince) and `ode23` (Bogacki–Shampine), with MATLAB error control, Refine output, tspan vectors, systems, backward integration and the sol struct;
- `odeset`/`odeget`;
- `integral2`, including function limits;
- `quad`;
- `integral` ArrayValued;
- `fminbnd`, MATLAB's Brent;
- `optimset`/`optimget`;
- `fminsearch` TolX/TolFun/MaxIter.

This absorbs the options part of #581.

T03 is met.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| M3-E3 ODE, quadrature, optimisation (T03) | #627 | [#658](https://github.com/superche/openmatlab/pull/658) | [job 115212367653](https://github.com/superche/openmatlab/actions/runs/38372406954/job/115212367653) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "[t, y] = ode45(@(t, y) -y, [0 0.5 1], 1); [t y]"
ans =

   0.0000   1.0000
   0.5000   0.6065
   1.0000   0.3679
$ openmatlab -e "o = odeset('RelTol', 1e-8); [t, y] = ode45(@(t, y) [y(2); -y(1)], [0 pi], [0; 1], o); y(end, :)"
ans =

   1.0e-01 *

    -0.0000   -10.0000
$ openmatlab -e "integral2(@(x, y) x.*y, 0, 1, 0, 2)"
ans =

1.0000
$ openmatlab -e "quad(@(x) x.^2, 0, 3)"
ans =

9
$ openmatlab -e "[x, fval] = fminbnd(@cos, 3, 4)"
x =

3.1416

fval =

-1.0000
$ openmatlab -e "fminsearch(@(p) (p(1)-1)^2 + (p(2)+2)^2, [0 0], optimset('TolX', 1e-8, 'TolFun', 1e-8))"
ans =

    1.0000   -2.0000
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1432 passed, 2 deselected, 8 xfailed in 18.62s
$ pytest tests/unit/test_ode_quad_opt.py tests/bdd/test_ode_quad_opt_bdd.py "tests/conformance/test_m3_conformance.py::test_m3_criterion[T03-m3_t03_calculus_ode_opt]" --tb=no
8 passed in 0.74s
$ pytest tests/conformance/test_m3_conformance.py --tb=no
4 passed, 4 xfailed in 0.62s
```

New cases: 5 unit tests (`tests/unit/test_ode_quad_opt.py`), 2 Gherkin scenarios (`features/ode_quad_opt.feature`), and conformance `m3_t03_calculus_ode_opt` (18 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F numerics.ode_quad_opt
numerics.ode_quad_opt            numerics   done     ode45/ode23, odeset, integral2, quad, integral ArrayValued, fminbnd, optimset
```

## Residuals (filed)

- [#657](https://github.com/superche/openmatlab/issues/657) (p2): stiff solvers, Events/Mass, deval, integral Waypoints, Display output.
- [#581](https://github.com/superche/openmatlab/issues/581): its integral/fminsearch options part is now delivered; the stats part goes to M3-E4 (#628).

## Milestone progress (M3)

- Criteria met: **3 / 7** (T01, T02, T03)
- Conformance scripts passing: **3 / 7** (strict xfail pending: T04, T05, T06, T07)
- Next: M3-E4 descriptive statistics (#628)
