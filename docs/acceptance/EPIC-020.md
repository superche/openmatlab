# EPIC-020 — delete via empty assign A(i)=[] / c(i)=[]

**Epic:** [#243](https://github.com/superche/openmatlab/issues/243) · Absorbs [#120](https://github.com/superche/openmatlab/issues/120), [#109](https://github.com/superche/openmatlab/issues/109)
**Milestone:** [M2 Octave-breadth](https://github.com/superche/openmatlab/milestone/2) — criterion **C06** (M2 priority rule)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `e64169bff7b3555510a603f0289e18327aaabc15` (PR #246) |
| **Evidence** | `d90872da2e6d56b72917eeca9c5dab827f748f82` (this stamp PR) |

## Acceptance checklist

1. \`v(2)=[]\` → \`[1 3 4]\` (C06) — **PASS**
2. Range/row-col delete; \`c(i)=[]\` — **PASS**
3. Maps / M2; #120 #109 closed; C06 met — **PASS**
4. This package + residual Issues — **PASS**

## Real smoke

```matlab
v = [1 2 3 4]; v(2) = [];   % [1 3 4]
c = {10, 20, 30}; c(2) = [];
A = [1 2; 3 4; 5 6]; A(2,:) = [];
```

\`pytest -m "unit or bdd"\`: **281 passed, 3 xfailed**.

## Milestone progress (M2)

- Criteria met: **8 / 11** (C01, C02, C03, C04, C05, C06, C07, C11)
- Conformance scripts passing: **8 / 11** (strict xfail pending: 3)
- This epic: C06 pending → **met**
- Remaining gaps (priority order — next epic takes #1):
1. **C08** (p0) `c08_grow_on_assign` — #119 #108
2. **C09** (p1) `c09_unique_issorted` — #97
3. **C10** (p1) `c10_cellfun` — #81
- Open p0 on M2: #119 #108

Doc: [docs/milestones/M2-octave-breadth.md](https://github.com/superche/openmatlab/blob/main/docs/milestones/M2-octave-breadth.md)

## Residuals (GitHub Issues — mandatory)

| Issue | Priority | Topic |
|-------|----------|-------|
| #247 | p1 | cell paren non-empty assign / multi-index delete |
| #248 | p2 | partial block A(i,j)=[] |
| #249 | p1 | logical mask delete coverage |
