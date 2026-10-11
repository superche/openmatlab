# EPIC-014 — zeros/ones/eye size-vector form

**Epic:** [#178](https://github.com/superche/openmatlab/issues/178) · Absorbs [#70](https://github.com/superche/openmatlab/issues/70)

**Milestone:** [Octave-breadth language & numerics](https://github.com/superche/openmatlab/milestone/2)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `8ecf077fdcf3edc421b8c02c68c1289ba019a85a` (PR #181) |
| **Evidence** | `f4be8b458d98572f0775ce512752e7c0f16433d7` (this stamp PR) |

## Acceptance checklist

1. `zeros([m n])` / `ones([m n])` → m×n; `zeros([n])` ≡ `zeros(n)` → n×n — **PASS**
2. `eye([m n])`; existing forms unchanged; N-D size vector → error — **PASS**
3. feature_map / catalog / ARCHITECTURE synced; #70 closed — **PASS**
4. This package + residual Issues filed (on milestone) — **PASS**

## Real smoke

```matlab
zeros([2 3])   % 2×3
ones([2 3])
eye([2 3])
zeros([4])     % 4×4 (1×1 size matrix ≡ scalar)
zeros([2 3 4]) % error (N-D deferred)
```

`pytest -m "unit or bdd"`: **240** passed at functional tip.

## Residuals (GitHub Issues — mandatory)

| Issue | Topic |
|-------|--------|
| #182 | N-D size vectors |
| #183 | `'like'` / class trailing args |
| #184 | zeros(size(A)) sugar gaps |

## Roadmap milestones

- [Workbench MVP](https://github.com/superche/openmatlab/milestone/1)
- [Octave-breadth language & numerics](https://github.com/superche/openmatlab/milestone/2)
- [Domain toolboxes](https://github.com/superche/openmatlab/milestone/3)
