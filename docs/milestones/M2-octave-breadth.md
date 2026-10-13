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


## Conformance script depth (honesty)

Scripts were **thickened in Epic #25** so titles match assertions more closely:

| Criterion | Added coverage |
|-----------|----------------|
| C04 | bare `pi`, `Inf`, `-Inf` (expected JSON tokens `"Inf"`/`"-Inf"`) |
| C06 | cell paren delete `c(2)=[]` via `yc=c{1}+c{2}` |
| C08 | cell content grow `c{3}=9` via `yg=c{1}+c{3}` |
| C10 | `cellfun(@sum)` and `cellfun(@max)` beyond `@numel` |

Harness: `tests/conformance/m2_expected.py` coerces Inf/NaN tokens. Remaining smoke thinness (matrix power, 2-D logical, etc.) tracked as residual Issues.

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
| C12 | N-D arrays: constructors, `A(i,j,k)`, `end`, grow, dim-3 reductions, N-D masks | c12_nd_arrays | p2 | #74 #182 #173 #259 #322 #330 | **met** (Epic #440) |
| C13 | Complex numbers: `3+4i`, `sqrt(-4)`, complex `^`, `abs/real/imag`, `max` by magnitude | c13_complex | p2 | #71 #229 #228 | **met** (Epic #449) |
| C14 | Integer classes, `zeros(...,'like',A)`, `"string"` scalars, char indexing | c14_int_string_classes | p2 | #72 #78 #183 | **met** (Epic #457) |
| C15 | String arrays `["a" "b"]`, `strings`, assign/grow/delete, text methods (`split`/`join`/`contains`/`replace`…) | c15_string_arrays | p2 | #459 #460 | **met** (Epic #482) |
| C16 | Sparse matrices: `sparse`/`full`/`nnz`, MATLAB sparsity rules, `S^p`, triplet display | c16_sparse | p2 | #451 | **met** (Epic #487) |
| C17 | Linear solve: `A\b`, `B/A` (square, least squares, basic solution), singular/rank warnings, `inv`/`det`/`rank`/`pinv` | c17_linear_solve | p2 | #496 | **met** (Epic #496) |
| C18 | Structs: `s.f`, nested and dynamic fields, struct arrays `s(i).f`, `struct()` with cells, field functions, cs-lists, regexp `names` | c18_structs | p2 | #506 #504 | **met** (Epic #506) |

Epic #15 (C05, p1) was opened before this rule. From Epic #16 on, the next epic
takes the **first pending row** in this table (p0 before p1, then table order).

## Required feature_ids at `done`

`lang.switch`, `lang.return`, `lang.index_end`, `runtime.array_assign_range`,
`libs.elmat_size_vector`, `libs.sort`, `libs.find`, `libs.cumsum`,
`libs.elmat_constructors`, `libs.reductions`, `libs.elfun`, plus the feature_ids
introduced for C02/C04/C06/C07/C08/C09/C10/C11 when their epics land.

Expected JSON may carry `"<var>:size": [r, c]` keys for direct shape asserts
(used by C06/C08 for cells, #302).

## Residual priority (open Issues on M2)

- **p0** (blocks exit): *(none open — exit criterion 3 satisfied)*
- **p1** (post-exit breadth): #184 — the only open p1 (snapshot 2026-10-12; earlier p1 lists were cleared by Epics #24–#32).
- **p2** (nice-to-have / non-goals): #130 #140 #141 #151 #152 #153 #164 #174 #197 #198 #208 #219 #239 #248 #270 #280 #281 #291 #292 #302 #311 #312 #336
  *(snapshot 2026-10-12; live list: `gh issue list --milestone "Octave-breadth language & numerics"`)*

## M2 close readiness (Epic #23)

All three exit criteria hold on `main` after Epic #23:

1. Conformance: C01–C11 `met`, 0 xfail.
2. Required feature_ids (incl. C02–C11 additions) at `done`.
3. No open `p0` Issues on milestone #2.

**Exit criteria still hold** (11/11, 0 p0). User accepted Epic #23 but **left milestone #2 OPEN** to continue p1/p2 breadth on M2.
Close remains optional/explicit; open p1/p2 stay on M2 until retargeted.

## Progress snapshot

After Epic #506 (structs, adds C18 p2): **18/18** criteria met. Remaining M2 work is residual p2 breadth (see open issues).

After Epic #496 (linear solve, adds C17 p2): **17/17** criteria met. Remaining M2 work is residual p2 breadth (see open issues).

After Epic #487 (sparse matrices, adds C16 p2): **16/16** criteria met. Remaining M2 work is residual p2 breadth (see open issues).

After Epic #482 (string arrays + methods, adds C15 p2): **15/15** criteria met. Remaining M2 work is residual p2 breadth (see open issues).

After Epic #457 (integer/string classes, adds C14 p2): **14/14** criteria met. Remaining M2 work is residual p2 breadth (see open issues).

After Epic #449 (complex numbers, adds C13 p2): **13/13** criteria met. Next epic: integer/string classes (#72 #78 #183).

After Epic #440 (N-D arrays, adds C12 p2): **12/12** criteria met. Next epics: complex numbers (#71 #229), then integer/string classes (#72 #78 #183).

After Epic #23: **11/11** criteria met. **M2 exit criteria complete.** Milestone left **OPEN** (user); next epics from residual p1 order (#247…).

After Epic #24 (#247 cell paren): still **11/11**. Next residual p1: **#249**.



After Epic #20: **8/11** criteria met. Next epic: **C08** (#119/#108, p0).


After Epic #19: **7/11** criteria met. Next epic: **C06** (#120/#109, p0).


After Epic #18: **6/11** criteria met. Next epic: **C07** (#162, p0).


After Epic #17: **5/11** criteria met. Next epic: **C11** (#193, p0).


After Epic #16: **4/11** criteria met. Next epic: **C04** (#192, p0).


After Epic #15: **3/11** criteria met. Next epic: **C02** (#191, p0).


Run `pytest tests/conformance -q` → passed (met) vs xfailed (pending).
Every `docs/acceptance/EPIC-NNN.md` records this in its **Milestone progress** section.
