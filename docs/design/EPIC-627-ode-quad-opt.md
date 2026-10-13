# EPIC-627: ODE solvers, quadrature and optimisation with options (M3-E3)

Criterion **T03** (`m3_t03_calculus_ode_opt`) in [M3](../milestones/M3-domain-toolboxes.md). The code is in core, in `openmatlab/libs/odeopt.py`. It also absorbs the integral/fminsearch-options part of #581.

## ODE solvers
- **Methods.** `ode45` uses Dormand–Prince 5(4); `ode23` uses Bogacki–Shampine 3(2), with FSAL.
- **Error control (MATLAB's).** `err = max(|est| ./ max(max(|y|,|ynew|), AbsTol/RelTol))`, and a step is accepted when `err <= RelTol`. Defaults are RelTol 1e-3 and AbsTol 1e-6, with `MaxStep = |tf-t0|/10` and MATLAB's initial-step heuristic. The step factor is clamped to [0.1 (or 0.2 after an accepted step), 5] with a safety factor of 0.8.
- **Output.** For `[t0 tf]`, every step is output with `Refine` (4 for ode45, 1 for ode23). For a longer `tspan` vector, output is at exactly those times, using cubic Hermite dense output. Integration may run backwards in time.
- **Results.** `[t, y]` gives a column `t` and one row of `y` per time. A single output gives a sol struct (`solver`, `x`, `y`).
- **Options.** `odeset`/`odeget` use the full MATLAB field list, case-insensitive with unique-prefix matching, and `odeset(old, ...)` merges.

## Quadrature
- `integral(..., 'ArrayValued', true)` uses vector G7–K15. Every other `integral` call goes to the existing core implementation unchanged: AbsTol/RelTol, Inf limits.
- `integral2(f, xa, xb, ya, yb)` is an iterated adaptive Gauss–Kronrod rule. `ya`/`yb` may be function handles of x, and AbsTol/RelTol are supported.
- `quad(f, a, b, tol)` is adaptive Simpson with Richardson correction. The second output is the number of function evaluations.

## Optimisation
- `fminbnd` follows MATLAB's algorithm (golden section plus parabolic interpolation) with TolX and MaxIter, and returns `[x, fval, exitflag]`.
- `optimset`/`optimget` follow the same conventions as odeset. Unknown names raise `MATLAB:optimset:InvalidPropName`.
- `fminsearch` now honours TolX/TolFun/MaxIter from an optimset struct; the core code was edited, not wrapped. `fzero` accepts an options struct, and its Brent iteration already converges to eps.

## Tests
- `tests/unit/test_ode_quad_opt.py`
- `features/ode_quad_opt.feature`
- conformance `m3_t03_calculus_ode_opt`

## Residuals
https://github.com/superche/openmatlab/issues/657
