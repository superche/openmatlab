# M2 — Octave-breadth language & numerics

GitHub milestone: https://github.com/superche/openmatlab/milestone/2

## Exit criteria (measurable)

M2 is **done** only when **all** of the following hold on `main`:

1. **Conformance suite green.** Every criterion in
   [`tests/conformance/m2_manifest.py`](../../tests/conformance/m2_manifest.py) has status
   `met`, and `pytest tests/conformance -m conformance` reports **0 xfail** for M2 scripts.
   Each script lives in `tests/conformance/scripts/<name>.m` with `<name>.expected.json`
   (expected workspace values, from public MATLAB documentation semantics).
2. **Required feature_ids at `done`** in `docs/feature_map.yaml` (list below).
3. **No open `p0` Issue** on this milestone.

Pending scripts run as **strict xfail**: once one starts passing, CI fails until
the manifest marks it `met`. Progress can't drift, and a criterion only counts as
met when its script actually passes.

## Criteria (priority order — epic selection MUST take the top unmet one)

| # | Criterion | Script | Priority | Tracking | Status |
|---|-----------|--------|----------|----------|--------|
| C02 | Bare colon subscripts `A(i,:)`, `A(:)` | c02_indexing | p0 | #191 | **met** (Epic #16) |
| C04 | Zero-arg constants `NaN`/`Inf`/`pi` in expressions | c04_numeric_builtins | p0 | #192 | **met** (Epic #17) |
| C11 | Scalar / square-matrix power `x^2` | c11_scalar_power_script | p0 | #193 | **met** (Epic #18) |
| C07 | Logical indexing read + LHS `v(v<0)=0` | c07_logical_indexing | p0 | #162 | **met** (Epic #19) |
| C06 | Delete `v(i)=[]` (arrays; cells #109) | c06_delete_elements | p0 | #120 #109 | **met** (Epic #20) |
| C08 | Grow on OOB assign `v(4)=7` (cells #108) | c08_grow_on_assign | p0 | #119 #108 | **met** (Epic #21) |
| C05 | `sort(...,'descend')`, `find(...,k,'first'/'last')` | c05_sort_find_options | p1 | #95 #96 | **met** (Epic #15) |
| C09 | `unique`, `issorted` | c09_unique_issorted | p1 | #97 | **met** (Epic #22) |
| C10 | `cellfun` + function handles `@f` | c10_cellfun | p1 | #81 | **met** (Epic #23) |
| C01 | Control flow (if/for/while/break/continue/switch) | c01_control_flow | p0 | — | met |
| C03 | Cells `{}` read/write/slice | c03_cells | p0 | — | met |

Epic #15 (C05, p1) was opened before this rule. From Epic #16 on, the next epic
takes the **first pending row** in this table (p0 before p1, then table order).

## Required feature_ids at `done`

`lang.switch`, `lang.return`, `lang.index_end`, `runtime.array_assign_range`,
`libs.elmat_size_vector`, `libs.sort`, `libs.find`, `libs.cumsum`,
`libs.elmat_constructors`, `libs.reductions`, `libs.elfun`, plus the feature_ids
introduced for C02/C04/C06/C07/C08/C09/C10/C11 when their epics land.

## Residual priority (open Issues on M2)

- **p0** (blocks exit): #191 #192 #193 #162 #120 #109 #119 #108
- **p1** (in exit criteria / high-value breadth): #247 #249 #237 #238 #227 #217 #218 #207 #209 #97 #81 #110 #83 #69 #80 #142 #184 #172
- **p2** (post-M2 or nice-to-have): #248 #239 #228 #229 #219 #208 #197 #198 #182 #183 #174 #173 #164 #153 #152 #151 #141 #140 #130 #78 #74 #72 #71

## Progress snapshot

After Epic #20: **8/11** criteria met. Next epic: **C08** (#119/#108, p0).


After Epic #19: **7/11** criteria met. Next epic: **C06** (#120/#109, p0).


After Epic #18: **6/11** criteria met. Next epic: **C07** (#162, p0).


After Epic #17: **5/11** criteria met. Next epic: **C11** (#193, p0).


After Epic #16: **4/11** criteria met. Next epic: **C04** (#192, p0).


After Epic #15: **3/11** criteria met. Next epic: **C02** (#191, p0).


Run `pytest tests/conformance -q` → passed (met) vs xfailed (pending).
Every `docs/acceptance/EPIC-NNN.md` records this in its **Milestone progress** section.
