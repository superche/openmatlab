# Acceptance evidence — Epic #9 (#126)

**Epic:** [#126 Loop continue statement](https://github.com/superche/openmatlab/issues/126)  
**Scope issues:** [#127](https://github.com/superche/openmatlab/issues/127) · [#128](https://github.com/superche/openmatlab/issues/128)  
**Functional tip** (step 1, PR #129): `214b9a55114f907ac67b7742cd68696daae264ac`  
**Evidence merge tip** (EPIC-009 + sync merged, PR #133): `ba81bf1059eb4ea99a853b1144fe343fdb55c832`  
**Captured:** 2026-10-11 18:58 CST on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Verdict

**Ready for user acceptance.** `continue` in `for`/`while` (innermost); outside-loop `continue`/`break` → EvalError. Tests were **not** weakened.

## Traceability

| Step | Issue | PR | Merge commit | CI `test` |
|------|-------|-----|--------------|-----------|
| 1 | #127 continue | [#129](https://github.com/superche/openmatlab/pull/129) | `214b9a55114f907ac67b7742cd68696daae264ac` | pass |
| 2–4 | #128 sync + EPIC-009 | [#133](https://github.com/superche/openmatlab/pull/133) | `ba81bf1059eb4ea99a853b1144fe343fdb55c832` | pass |

## Feature map

`lang.continue` → **done** per `docs/design/ITER-128-epic9-done-criteria.md`.
Counts: **done=42, partial=9, stub=2**.

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
213 passed, 2 deselected
```

## Smoke — CLI transcripts (functional tip `214b9a5`)

```text
$ openmatlab -e "s = 0; for i = 1:5; if i == 3; continue; end; s = s + i; end; s"
ans =

12

ans =

12

$ openmatlab -e "t = 0; n = 0; while n < 4; n = n + 1; if n == 2; continue; end; t = t + n; end; t"
ans =

8

ans =

8

$ openmatlab -e "continue"
error: continue outside of a for or while loop
```

## Residual (canonical Issues — PROCESS § Residual Issues)

| Residual | Issue |
|----------|-------|
| Labeled break/continue | [#130](https://github.com/superche/openmatlab/issues/130) |
| `return` statement | [#131](https://github.com/superche/openmatlab/issues/131) |
| switch/case | [#132](https://github.com/superche/openmatlab/issues/132) |

## How to re-run

```bash
git checkout ba81bf1059eb4ea99a853b1144fe343fdb55c832   # evidence tip (functional: `214b9a55114f907ac67b7742cd68696daae264ac`)
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab -e "s = 0; for i = 1:5; if i == 3; continue; end; s = s + i; end; s"
```
