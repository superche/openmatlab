# EPIC-010 — return statement in .m functions

**Epic:** [#136](https://github.com/superche/openmatlab/issues/136) · Absorbs [#131](https://github.com/superche/openmatlab/issues/131)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `81a9f49660af14781a4bc8173896680211e7dfd9` (PR #139) |
| **Evidence** | `f0df2d8e6820b2d399dbd0c447c3232a4032b6d5` (this stamp PR) |

## Acceptance checklist

1. `return` inside `.m` function stops remaining body; assigned outputs returned — **PASS**
2. `return` in scripts (via `run`) exits early; top-level REPL → EvalError — **PASS**
3. feature_map / catalog / ARCHITECTURE synced; #131 closed — **PASS**
4. This package + residual Issues filed — **PASS** (see below)

## Real smoke

```matlab
% early.m: function y = early(x); y = x+1; return; y = x+100; end
y = early(5);   % → 6
run('setup.m'); % a=1; return; a=99; → a is 1
return;         % EvalError at toplevel
```

`pytest -m "unit or bdd"`: **218** passed at functional tip.

## Residuals (GitHub Issues — mandatory)

| Issue | Topic |
|-------|--------|
| #140 | `return` with expression / multi-output helpers |
| #141 | Nested functions `return` targeting outer |
| #142 | Bare script name without `run` (related control flow) |

Non-goals deferred: switch/case (#132), labeled break/continue (#130).
