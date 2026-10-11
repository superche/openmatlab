# EPIC-015 — sort descend + find first/last

**Epic:** [#188](https://github.com/superche/openmatlab/issues/188) · Absorbs [#95](https://github.com/superche/openmatlab/issues/95), [#96](https://github.com/superche/openmatlab/issues/96)
**Milestone:** [M2 Octave-breadth](https://github.com/superche/openmatlab/milestone/2) — criterion **C05**

## Tips (dual)

| Tip | SHA |
|-----|-----|
| **Functional** | `87cdcf8a11b1fd69bc02c81c672a61d1af984b18` (PR #195) |
| **Evidence** | `cc1d70af48e9f55783841aede0e7550b379f45f0` (this stamp PR) |

## Acceptance checklist

1. `sort(A,'descend')`, `sort(A,dim,'descend')`, `[B,I]` stable 1-based — **PASS**
2. `find(X,k)`, `find(X,k,'first'|'last')`; row input → row output — **PASS**
3. feature_map / catalog / ARCHITECTURE / M2 doc synced; #95 #96 closed — **PASS**
4. This package + residual Issues (on M2, prioritized) — **PASS**

## Real smoke

```matlab
[b, i] = sort([3 1 2], 'descend')   % b = [3 2 1], i = [1 3 2]
f = find([0 1 1 0 1], 2, 'last')    % [3 5]
```

`pytest -m "unit or bdd"`: **251 passed, 8 xfailed** (strict xfail = pending M2 criteria).

## Milestone progress (M2)

- Criteria met: **3 / 11** (C01, C03, C05)
- Conformance scripts passing: **3 / 11** (strict xfail pending: 8)
- This epic: C05 pending → **met**
- Remaining gaps (priority order — next epic takes #1):
1. **C02** (p0) `c02_indexing` — #191
2. **C04** (p0) `c04_numeric_builtins` — #192
3. **C11** (p0) `c11_scalar_power_script` — #193
4. **C07** (p0) `c07_logical_indexing` — #162
5. **C06** (p0) `c06_delete_elements` — #120 #109
6. **C08** (p0) `c08_grow_on_assign` — #119 #108
7. **C09** (p1) `c09_unique_issorted` — #97
8. **C10** (p1) `c10_cellfun` — #81
- Open p0 Issues on M2: #191 #192 #193 #162 #120 #109 #119 #108

Doc: [docs/milestones/M2-octave-breadth.md](https://github.com/superche/openmatlab/blob/main/docs/milestones/M2-octave-breadth.md)

## Residuals (GitHub Issues — mandatory)

| Issue | Priority | Topic |
|-------|----------|-------|
| #196 | p1 | find NaN-as-zero / empty-row orientation (existing tests encode non-MATLAB behavior; needs sign-off to correct) |
| #197 | p2 | sort ComparisonMethod / MissingPlacement |
| #198 | p2 | sort char / cellstr |
