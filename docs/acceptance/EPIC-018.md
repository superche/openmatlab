# EPIC-018 — scalar / square-matrix power ^

**Epic:** [#223](https://github.com/superche/openmatlab/issues/223) · Absorbs [#193](https://github.com/superche/openmatlab/issues/193)
**Milestone:** [M2 Octave-breadth](https://github.com/superche/openmatlab/milestone/2) — criterion **C11** (M2 priority rule)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `f559fa48dd42b9af56d4023ea4382dbaa5a23870` (PR #226) |
| **Evidence** | `EVIDENCE_SHA_PLACEHOLDER` (this stamp PR) |

## Acceptance checklist

1. Scalar \`i^2\`; C11 script (\`x=14\`, \`y=3\`) — **PASS**
2. Square \`A^n\` integer; clear error otherwise; \`.\^\` unchanged — **PASS**
3. Maps / M2; #193 closed; C11 met — **PASS**
4. This package + residual Issues — **PASS**

## Real smoke

```matlab
x = 0; for i = 1:3; x = x + i^2; end   % 14
y = sqrt(x - 5);                        % 3
A = [1 1; 0 1]; B = A^3;                % [1 3; 0 1]
```

\`pytest -m "unit or bdd"\`: **271 passed, 5 xfailed**.

## Milestone progress (M2)

- Criteria met: **6 / 11** (C01, C02, C03, C04, C05, C11)
- Conformance scripts passing: **6 / 11** (strict xfail pending: 5)
- This epic: C11 pending → **met**
- Remaining gaps (priority order — next epic takes #1):
1. **C07** (p0) `c07_logical_indexing` — #162
2. **C06** (p0) `c06_delete_elements` — #120 #109
3. **C08** (p0) `c08_grow_on_assign` — #119 #108
4. **C09** (p1) `c09_unique_issorted` — #97
5. **C10** (p1) `c10_cellfun` — #81
- Open p0 on M2: #162 #120 #109 #119 #108

Doc: [docs/milestones/M2-octave-breadth.md](https://github.com/superche/openmatlab/blob/main/docs/milestones/M2-octave-breadth.md)

## Residuals (GitHub Issues — mandatory)

| Issue | Priority | Topic |
|-------|----------|-------|
| #227 | p1 | wrap NumericsError as EvalError for ^ |
| #228 | p2 | 2^A / fractional / expm |
| #229 | p2 | complex / sparse matrix power |
