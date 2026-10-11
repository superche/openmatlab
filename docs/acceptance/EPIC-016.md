# EPIC-016 — bare colon subscript A(i,:) / A(:)

**Epic:** [#203](https://github.com/superche/openmatlab/issues/203) · Absorbs [#191](https://github.com/superche/openmatlab/issues/191)
**Milestone:** [M2 Octave-breadth](https://github.com/superche/openmatlab/milestone/2) — criterion **C02** (selected by M2 priority rule)

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `b61c3d421163e651e4e5d10c615d700897cd015d` (PR #206) |
| **Evidence** | `EVIDENCE_SHA_PLACEHOLDER` (this stamp PR) |

## Acceptance checklist

1. Read \`A(:)\`, \`A(i,:)\`, \`A(:,j)\` — **PASS**
2. Assign \`A(1,:)=row\` — **PASS** (C02 script)
3. Maps / ARCHITECTURE / M2 doc; #191 closed; C02 met — **PASS**
4. This package + prioritized residual Issues — **PASS**

## Real smoke

```matlab
A = zeros(2,3); A(1,:) = [1 2 3]; A(2,end) = 9; A(1:2,1) = [7;8];
x = A(end); v = A(2,1:end);
```

`pytest -m "unit or bdd"`: **257 passed, 7 xfailed**.

## Milestone progress (M2)

- Criteria met: **4 / 11** (C01, C02, C03, C05)
- Conformance scripts passing: **4 / 11** (strict xfail pending: 7)
- This epic: C02 pending → **met**
- Remaining gaps (priority order — next epic takes #1):
1. **C04** (p0) \`c04_numeric_builtins\` — #192
2. **C11** (p0) \`c11_scalar_power_script\` — #193
3. **C07** (p0) \`c07_logical_indexing\` — #162
4. **C06** (p0) \`c06_delete_elements\` — #120 #109
5. **C08** (p0) \`c08_grow_on_assign\` — #119 #108
6. **C09** (p1) \`c09_unique_issorted\` — #97
7. **C10** (p1) \`c10_cellfun\` — #81
- Open p0 on M2: #192 #193 #162 #120 #109 #119 #108

Doc: [docs/milestones/M2-octave-breadth.md](https://github.com/superche/openmatlab/blob/main/docs/milestones/M2-octave-breadth.md)

## Residuals (GitHub Issues — mandatory)

| Issue | Priority | Topic |
|-------|----------|-------|
| #207 | p1 | stepped / incomplete colon polish |
| #208 | p2 | A(:) edge orientation |
| #209 | p1 | bare colon in cell {} |
