# EPIC-011 — switch / case / otherwise

**Epic:** [#147](https://github.com/superche/openmatlab/issues/147) · Absorbs [#132](https://github.com/superche/openmatlab/issues/132)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `0aae9a296a052f6909500db525b63da5ab450209` (PR #150) |
| **Evidence** | `df6c1b4a2cf3780579efe85c0fe2a654c21525cc` (this stamp PR) |

## Acceptance checklist

1. `switch` / `case` / `otherwise` / `end`; first match; no fall-through — **PASS**
2. Multi-value `case {a,b}`; no match + no otherwise → no-op — **PASS**
3. feature_map / catalog / ARCHITECTURE synced; #132 closed — **PASS**
4. This package + residual Issues filed — **PASS**

## Real smoke

```matlab
switch x
  case 1
    y = 10;
  case {2, 3}
    y = 20;
  otherwise
    y = 0;
end
```

`pytest -m "unit or bdd"`: **224** passed at functional tip.

## Residuals (GitHub Issues — mandatory)

| Issue | Topic |
|-------|--------|
| #151 | fall-through (non-default) |
| #152 | non-scalar / string-class case match |
| #153 | case comma-list without braces |

Non-goals deferred: labeled break/continue (#130).
