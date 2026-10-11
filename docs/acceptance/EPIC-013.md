# EPIC-013 — end keyword in array indexing

**Epic:** [#168](https://github.com/superche/openmatlab/issues/168) · Absorbs [#163](https://github.com/superche/openmatlab/issues/163)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `5fef81f8fcf9147e3b4130b1cbe4eaa8d73bf533` (PR #171) |
| **Evidence** | `EVIDENCE_SHA_PLACEHOLDER` (this stamp PR) |

## Acceptance checklist

1. Read: `A(end)`, `A(1,end)`, `A(1:end)` — **PASS**
2. Assign: `A(end)=v`, `A(1:end)=vec`; `end-1` — **PASS**
3. feature_map / catalog / ARCHITECTURE synced; #163 closed — **PASS**
4. This package + residual Issues filed — **PASS**

## Real smoke

```matlab
A = [10 20 30 40]; x = A(end);      % 40
A = [1 2 3; 4 5 6]; y = A(1,end);   % 3
A(1:end) = [1 2 3 4];
A(end-1) = 9;
```

`pytest -m "unit or bdd"`: **235** passed at functional tip.

## Residuals (GitHub Issues — mandatory)

| Issue | Topic |
|-------|--------|
| #172 | end in cell {} indexing |
| #173 | end with N-D (>2 subscripts) |
| #174 | clearer error for end in call args |

Non-goals deferred: logical LHS (#162), `A(i)=[]` (#120).
