# M10 — Tables and data types

GitHub milestone: https://github.com/superche/openmatlab/milestone/10

**Related:**
- [M8 Object system](M8-object-system.md) (closed): indexing hooks and display used by `table`.
- [M7 core language & I/O](M7-core-language-io.md) (closed): `datetime`/`duration`, file I/O.
- [M11 Debugger and Workbench](M11-debugger-workbench.md) runs interleaved.
- [`../GAP-ANALYSIS.md`](../GAP-ANALYSIS.md) ("Tables etc." row).

## Intent

MATLAB's base heterogeneous-data types in core, clean-room from public documentation: `table`, `categorical`, `timetable` (p2), on the M8 class model and the M7 `datetime`/`duration`, with `readtable`/`writetable` and the usual table verbs (`sortrows`, `join`, `groupsummary`, …).

Approved by Shaw on 2026-10-16. Decisions: `table` uses its **own columnar storage** (a column store of existing `Value`s; no pandas dependency); `timetable` (T10) is **included as p2 and cuttable**.

## Exit criteria (measurable)

M10 is **done** only when **all** of these hold on `main`:

1. **Conformance.** Every criterion in [`tests/conformance/m10_manifest.py`](../../tests/conformance/m10_manifest.py) is `met`, and `pytest tests/conformance/test_m10_conformance.py` reports **0 xfail** (T10 may instead be cut to a non-goal by Shaw).
2. **No open `p0` issue** on milestone/10.
3. **No Python traceback.** A probe sweep over the table/categorical/readtable features shows no Python exception reaching the user.
4. **Docs.** No doc drift; CI on `main` is green; each epic has an acceptance package (`docs/acceptance/EPIC-NNN.md`) accepted by the user.

Pending scripts run as **strict xfail** and flip to `met` in the PR that makes them pass. Scripts are thick (10–17 checked values each).

## Criteria

| # | Criterion | Script | Priority | Epic | Status |
|---|-----------|--------|----------|------|--------|
| T01 | `table` construction (`table(a,b)`, `'VariableNames'`, `'RowNames'`, `array2table`, `cell2table`, `struct2table`), `height`/`width`/`size`, `Properties.VariableNames`/`RowNames`, display, `istable`/`class` | m10_t01_table_construct_display | p0 | #691 | met (Epic #691; residual #709) |
| T02 | Indexing: `T.Var`, `T{r,c}`, `T(r,c)`, logical rows, add/delete variables and rows, `end`, `[T1;T2]`/`[T1,T2]` with name checks and errors | m10_t02_table_indexing | p0 | #691 | met (Epic #691; residual #709) |
| T03 | `table2array`/`table2cell`/`table2struct`, `summary`, `head`/`tail`, `isempty`, `rowfun`/`varfun`, `removevars`/`renamevars`/`movevars`/`addvars` | m10_t03_table_conversion_varfun | p1 | #693 | pending |
| T04 | `categorical`: valueset/catnames/`Ordinal`, `categories`, `countcats`, `addcats`/`removecats`/`mergecats`/`renamecats`, comparisons, `<undefined>`/`isundefined`, table variable | m10_t04_categorical | p0 | #692 | met (Epic #692; residual #717) |
| T05 | `sortrows(T,vars,dir)`, `issortedrows`, `sort`/`unique`/`ismember` on categorical, string and table | m10_t05_sortrows_sets | p1 | #693 (#585) | pending |
| T06 | `join`, `innerjoin`, `outerjoin` (`'Type'`, `'MergeKeys'`, `'Keys'`), key-mismatch errors | m10_t06_joins | p1 | #696 | pending |
| T07 | `findgroups`, `splitapply`, `groupsummary` (mean/sum/min/max, multiple groups), `groupcounts` | m10_t07_grouping | p1 | #696 | pending |
| T08 | `readtable`/`writetable` CSV/delimited round-trip (header, `'VariableNames'`, mixed columns, `'Delimiter'`, missing → NaN, datetime columns), `readcell`/`writecell` | m10_t08_readtable_writetable | p0 | #694 (#577) | met (Epic #694; residual #721) |
| T09 | datetime arrays: column vectors, concatenation, NaT/`isnat`, `InputFormat`/`Format`, `dateshift`, `between`, `caldays`/`calmonths`, component assignment with rollover | m10_t09_datetime_arrays | p1 | #695 (#602, #673) | met (Epic #695; residual #733) |
| T10 | `timetable`, `table2timetable`, `timerange`/`withtol`, `retime`, `synchronize`, `lag` | m10_t10_timetable | p2 (cuttable) | #697 | pending |

## Epics (approved order, interleaved with M11)

1. **T-E1 #691 (p0):** `table` core — T01, T02. Runs after D-E1.
2. **T-E2 #692 (p0):** `categorical` — T04.
3. **T-E4 #694 (p0):** `readtable`/`writetable` — T08.
4. **T-E5 #695 (p1):** datetime arrays — T09 (can run in parallel).
5. **T-E3 #693 (p1):** table utilities, sorting and sets — T03, T05.
6. **T-E6 #696 (p1):** joins and grouping — T06, T07.
7. **T-E7 #697 (p2):** `timetable` — T10 (cuttable).

Absorbed residuals are referenced, not moved: #577 (`readtable`), #585 (set ops on table/string), #602 (datetime array subset; time zones stay out), #665 (table/datetime in `jsonencode`, optional), #673 (datetime component assignment).

## Non-goals

Spreadsheet (`.xlsx`), Parquet/HDF5 I/O; tall arrays, `datastore`, `dataset`; MAT v7.3 tables; full time-zone database; performance parity on big tables; pandas as a dependency.

## Risks and design questions

- **Indexing semantics:** `T{...}`/`T(...)`/`T.x(i)=` chains through the M8 subsref machinery without recursion (#653).
- **Display fidelity:** criteria pin a minimal format; full MATLAB layout is residual.
- **readtable heuristics:** documented defaults pinned in T08; edge cases become residuals.

## Progress snapshot

M10 opened 2026-10-16. **5 / 10** criteria met: T01, T02 (Epic #691, [design](../design/EPIC-691-table-core.md)), T04 (Epic #692, [design](../design/EPIC-692-categorical.md)), T08 (Epic #694, [design](../design/EPIC-694-readtable.md)), T09 (Epic #695, [design](../design/EPIC-695-datetime-arrays.md)). Next: T-E3 (#693) table utilities, sorting and sets, interleaved with D-E5 (#702).
