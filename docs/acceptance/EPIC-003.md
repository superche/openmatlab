# Acceptance evidence — Epic #3 (#33)

**Epic:** [#33 Scripts + while/break](https://github.com/superche/openmatlab/issues/33)  
**Scope issues:** [#34](https://github.com/superche/openmatlab/issues/34) · [#35](https://github.com/superche/openmatlab/issues/35) · [#36](https://github.com/superche/openmatlab/issues/36) · [#37](https://github.com/superche/openmatlab/issues/37)  
**Functional tip** (ordered steps 1–3 code complete, PR #40): `76bb5c2b1440ac2e4e964739b12732866948e9e0`  
**Evidence merge tip:** *(filled after this acceptance PR merges onto `main`)*  
**Captured:** 2026-10-11 17:22 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Verdict

**Accepted** pending evidence-merge tip stamp: ordered acceptance 1–3 green (`while`/`break`, script `.m`, `run`), step 4 docs sync in this PR, dual-tip pattern per PROCESS.

## Traceability — Issues → PRs → merge SHAs

| Step | Issue | PR | Merge commit | CI |
|------|-------|-----|--------------|-----|
| 1 | #34 while+break | [#38](https://github.com/superche/openmatlab/pull/38) | `3f5a2dab3e2392ec67e9945bc9165fc99196633a` | `test` green |
| 2 | #35 script .m | [#39](https://github.com/superche/openmatlab/pull/39) | `050fa7b43cffc64389988ab7bbab79d4bfc4a558` | `test` green |
| 3 | #36 run() | [#40](https://github.com/superche/openmatlab/pull/40) | `76bb5c2b1440ac2e4e964739b12732866948e9e0` | `test` green |
| 4–5 | #37 sync + EPIC-003 | *(this PR)* | evidence merge tip | `test` required |

## Feature map (functional tip)

`openmatlab features` → **counts: done=25, partial=9, stub=2** (36 features).

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
........................................................................ [ 67%]
..................................                                       [100%]
106 passed, 2 deselected in 0.68s
```

## Smoke — ordered capabilities (real transcript)

```text
while x 2.0
script n 2.0
path run k 11.0
```

(`while` increment; `run` on script with `while`/`break`; `addpath` + `run("setup")`.)

CLI:

```text
$ openmatlab -e "1+1"
ans =

2
```

## Residual (explicit non-goals)

`continue`; bare script name without `run`; single-quoted char/cells; rich toolboxes.

## How to re-run

Checkout the **evidence merge tip** (or `main`) to read this file:

```bash
git checkout main   # after evidence PR merges
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
```

Functional-only tree (no EPIC-003 yet): `76bb5c2b1440ac2e4e964739b12732866948e9e0`.
