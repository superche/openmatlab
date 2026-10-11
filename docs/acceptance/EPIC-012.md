# EPIC-012 — range / non-scalar indexed assignment

**Epic:** [#158](https://github.com/superche/openmatlab/issues/158) · Absorbs [#121](https://github.com/superche/openmatlab/issues/121), [#122](https://github.com/superche/openmatlab/issues/122)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `72e81d76463fa9b06045ce0ba50480590bbac39a` (PR #161) |
| **Evidence** | `a9d3300c281586772259d1b2d91f1ee4d4034a53` (this stamp PR) |

## Acceptance checklist

1. Linear / 2-sub range LHS with matching RHS — **PASS**
2. Scalar RHS broadcasts; numel mismatch → EvalError — **PASS**
3. feature_map / catalog / ARCHITECTURE synced; #121 #122 closed — **PASS**
4. This package + residual Issues filed — **PASS**

## Real smoke

```matlab
A = [1 2 3 4]; A(1:3) = [10 20 30];
A = zeros(2); A(1:2,1:2) = [1 2; 3 4];
A(1:2) = 7;           % scalar broadcast
A(1:2) = [1 2 3];     % EvalError numel
```

`pytest -m "unit or bdd"`: **230** passed at functional tip.

## Residuals (GitHub Issues — mandatory)

| Issue | Topic |
|-------|--------|
| #162 | logical indexing LHS |
| #163 | `end` in indexed assignment |
| #164 | RHS shape-strict (beyond numel) |

Non-goals deferred: `A(i)=[]` delete (#120), grow-on-write (#119), N-D (#74).
