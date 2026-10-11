# EPIC-019 — logical indexing read + LHS assign

**Epic:** [#233](https://github.com/superche/openmatlab/issues/233) · Absorbs [#162](https://github.com/superche/openmatlab/issues/162)
**Milestone:** [M2 Octave-breadth](https://github.com/superche/openmatlab/milestone/2) — criterion **C07** (M2 priority rule)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `be32e01fd2109c05502086513bc76a1989440e91` (PR #236) |
| **Evidence** | `EVIDENCE_SHA_PLACEHOLDER` (this stamp PR) |

## Acceptance checklist

1. Read \`p = v(v > 0)\` — **PASS**
2. Assign \`v(v < 0) = 0\` — **PASS**; C07 met — **PASS**
3. Maps / M2; #162 closed — **PASS**
4. This package + residual Issues — **PASS**

## Real smoke

```matlab
v = [5 -1 3 -2];
p = v(v > 0);      % [5 3]
v(v < 0) = 0;      % [5 0 3 0]
```

\`pytest -m "unit or bdd"\`: **276 passed, 4 xfailed**.

## Milestone progress (M2)

- Criteria met: **7 / 11** (C01, C02, C03, C04, C05, C07, C11)
- Conformance scripts passing: **7 / 11** (strict xfail pending: 4)
- This epic: C07 pending → **met**
- Remaining gaps (priority order — next epic takes #1):
1. **C06** (p0) `c06_delete_elements` — #120 #109
2. **C08** (p0) `c08_grow_on_assign` — #119 #108
3. **C09** (p1) `c09_unique_issorted` — #97
4. **C10** (p1) `c10_cellfun` — #81
- Open p0 on M2: #120 #109 #119 #108

Doc: [docs/milestones/M2-octave-breadth.md](https://github.com/superche/openmatlab/blob/main/docs/milestones/M2-octave-breadth.md)

## Residuals (GitHub Issues — mandatory)

| Issue | Priority | Topic |
|-------|----------|-------|
| #237 | p1 | 2-D logical A(L1,L2) |
| #238 | p1 | logical() constructor |
| #239 | p2 | display / promotion polish |
