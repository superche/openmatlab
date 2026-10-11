# Acceptance evidence — Epic #2 (#19)

**Epic:** [#19 Workbench depth](https://github.com/superche/openmatlab/issues/19)  
**Scope issues:** [#20](https://github.com/superche/openmatlab/issues/20) · [#21](https://github.com/superche/openmatlab/issues/21) · [#22](https://github.com/superche/openmatlab/issues/22) · [#23](https://github.com/superche/openmatlab/issues/23) · [#24](https://github.com/superche/openmatlab/issues/24)  
**Functional tip** (ordered steps 1–5 code complete, PR #29): `02f113fe0b034178dba7c5c5ad33fad35231d9fc`  
**Evidence merge tip** (this doc on `main`, PR #30): `6650784360978f59109fa072e7cc765840021e07`  
**Captured:** 2026-10-11 16:04 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Verdict

**Accepted.** Ordered acceptance 1–5 green: language `addpath`/`which`, multi-return assign, minimal `if`/`for`, interactive plot policy (`show`/`drawnow`, Agg CI default), and key `feature_id`s promoted to defensible `done` per ITER-024.

## Traceability — Issues → PRs → merge SHAs

| Step | Issue | PR | Merge commit | CI |
|------|-------|-----|--------------|-----|
| 1 | #20 addpath/which | [#25](https://github.com/superche/openmatlab/pull/25) | `915bb370c472cfcaba5c2f45e1757d3aa6a395cb` | `test` green |
| 2 | #21 multi-return | [#26](https://github.com/superche/openmatlab/pull/26) | `a3222b9e1efbea1fe85d077f845da0cafbbc4541` | `test` green |
| 3 | #22 if/for | [#27](https://github.com/superche/openmatlab/pull/27) | `2dde60c36136c940922561c0c5d822b4c66c730d` | `test` green |
| 4 | #23 interactive plot | [#28](https://github.com/superche/openmatlab/pull/28) | `9c83a2ced5c8c9552f95281fa6eb9e3fd9fa9fb8` | `test` green |
| 5 | #24 promote done | [#29](https://github.com/superche/openmatlab/pull/29) | `02f113fe0b034178dba7c5c5ad33fad35231d9fc` | [run](https://github.com/superche/openmatlab/actions/runs/38123524555) success |

## Feature map (tip)

`openmatlab features` → **counts: done=24, partial=10, stub=2** (36 features).  
Promotions documented in `docs/design/ITER-024-feature-done-criteria.md`.

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
........................................................................ [ 79%]
...................                                                      [100%]
91 passed, 2 deselected in 0.73s
```

## Smoke — ordered capabilities (real transcript)

Session with temp `swap.m` on path:

```text
which ans: /tmp/…/swap.m
u 2.0 v 1.0
for sum 6.0
if ok 1.0
show ans 1.0
interactive False
```

CLI:

```text
$ openmatlab -e "A = [1 2; 3 4] * [1; 0]"
A =

[[1.]
 [3.]]
```

Policy check: under default/CI, `Session.create_default()` keeps `graphics.interactive False`; `show()` is Agg no-op returning scalar 1. Interactive path: `OPENMATLAB_PLOT_INTERACTIVE=1` when not `CI`/`GITHUB_ACTIONS` (unit-tested).

## Residual (explicit non-goals)

`while`/`break`/`continue`, single-quoted char vectors/cells, nested functions, rich toolboxes, GUI tweak widgets beyond Matplotlib `show`.

## How to re-run

To read this evidence file and match `main` docs, checkout the **evidence merge tip** (or `main`):

```bash
git checkout 6650784360978f59109fa072e7cc765840021e07   # or: git checkout main
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab -e "A = [1 2; 3 4] * [1; 0]"
```

To reproduce only the step-5 **functional** tree (no `EPIC-002.md` yet), use `02f113fe0b034178dba7c5c5ad33fad35231d9fc`.
