# EPIC-017 — bare NaN / Inf / pi as zero-arg constants

**Epic:** [#213](https://github.com/superche/openmatlab/issues/213) · Absorbs [#192](https://github.com/superche/openmatlab/issues/192)
**Milestone:** [M2 Octave-breadth](https://github.com/superche/openmatlab/milestone/2) — criterion **C04** (M2 priority rule)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `a37cd57ffeb0b5763ffbb2a82e3b3a7211f65770` (PR #216) |
| **Evidence** | `EVIDENCE_SHA_PLACEHOLDER` (this stamp PR) |

## Acceptance checklist

1. Bare \`NaN\`/\`Inf\`/\`pi\` in expressions; workspace shadow — **PASS**
2. \`nan()\` unchanged; C04 conformance met — **PASS**
3. Maps / M2 doc; #192 closed — **PASS**
4. This package + residual Issues (p0/p1/p2) — **PASS**

## Real smoke

```matlab
m = max([1 NaN 3]);   % 3
x = pi; y = Inf; z = -Inf;
NaN = 7; w = NaN;     % 7 (shadow)
```

\`pytest -m "unit or bdd"\`: **264 passed, 6 xfailed**.

## Milestone progress (M2)

- Criteria met: **5 / 11** (C01, C02, C03, C04, C05)
- Conformance scripts passing: **5 / 11** (strict xfail pending: 6)
- This epic: C04 pending → **met**
- Remaining gaps (priority order — next epic takes #1):
1. **C11** (p0) `c11_scalar_power_script` — #193
2. **C07** (p0) `c07_logical_indexing` — #162
3. **C06** (p0) `c06_delete_elements` — #120 #109
4. **C08** (p0) `c08_grow_on_assign` — #119 #108
5. **C09** (p1) `c09_unique_issorted` — #97
6. **C10** (p1) `c10_cellfun` — #81
- Open p0 on M2: #193 #162 #120 #109 #119 #108

Doc: [docs/milestones/M2-octave-breadth.md](https://github.com/superche/openmatlab/blob/main/docs/milestones/M2-octave-breadth.md)

## Residuals (GitHub Issues — mandatory)

| Issue | Priority | Topic |
|-------|----------|-------|
| #217 | p1 | eps / realmax / realmin |
| #218 | p1 | bare i / j imaginary |
| #219 | p2 | true / false |

Also recorded: PROCESS/AGENTS now require **all todos as GitHub Issues** (PR #212).
