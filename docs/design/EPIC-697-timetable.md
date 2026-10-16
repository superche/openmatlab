# Epic #697 (T-E7): timetable

Milestone: [M10 Tables and data types](../milestones/M10-tables.md), criterion T10.

## Design

- **Value.** `runtime/timetable_value.py` `TimetableValue` subclasses `TableValue` (same column store, `is_table` dispatch for `{}`/`()`/`.` indexing, `height`/`width`, variable add/delete). Row names are replaced by `rowtimes`, an n×1 `datetime` or `duration`; `dimnames` defaults to `{'Time','Variables'}`, and `timetable(t, x)` names the time dimension after the workspace variable `t` (MATLAB). `TT.<timeName>` and `TT.Properties.RowTimes` return the row times. `class` is `timetable`; `istable(TT)` is false and `istimetable(TT)` true, as in MATLAB.
- **Row subscripts.** Numbers and logicals as for tables; a datetime/duration (or date text) selects the rows at exactly those times (tolerance 1e-9 days for floating arithmetic); `timerange(a, b, type)` (default `'openright'`; `'closed'`, `'open'`, `'openleft'`, `'closedleft'`, `'closedright'`) and `withtol(times, tol)` select by interval/tolerance. Row selection carries the row times along.
- **Growth and concatenation.** Rows added by indexed assignment get missing row times (NaT/NaN). `[TT1; TT2]` concatenates row times; mixing a datetime and a duration timetable is an error.
- **Conversion.** `table2timetable(T)` uses the first datetime/duration variable (or `'RowTimes'`, a name or vector); `timetable2table` puts the row times back as the first variable.
- **retime / synchronize.** A new time vector comes from `'regular'` + `'TimeStep'`/`'SampleRate'`, `'secondly'`…`'weekly'`, `'union'`/`'intersection'`/`'first'`/`'last'`/`'commonrange'`, or an explicit time vector. Aggregation methods (`mean sum min max median prod count firstvalue lastvalue`) reduce each bin `[t_k, t_{k+1})` (last bin closed); fill methods (`previous next nearest linear fillwithmissing fillwithconstant`) read rows at/around each time, filling with the type's missing value. `synchronize` prefixes nothing and suffixes duplicate variable names with the input's workspace name (`v_A`, `v_B`).
- **lag.** `lag(TT, n)` shifts down by n rows (negative = lead), filling with missing; a duration lag requires regular row times.
- **Display.** Same layout as `table` with the time column first under its dimension name; datetime row times use one format for the whole column.

## Adversarial review

| Probe | Finding | Resolution |
|---|---|---|
| `TT.t` | first cut used `'Time'` and `TT.t` failed | dimension named from the caller's variable |
| Datetime row-time column | midnight row printed date-only while others had times | uniform column format |
| `[TT; TT]`, `TT(end+1,:) = {…}` | copy without row times raised | concatenate row times / pad with NaT |
| `retime` on cell variables with `'mean'` | must be a MATLAB error, not a traceback | `MATLAB:timetable:retime:NonNumericVar` |
| `'regular'` without `TimeStep`, unknown basis/method, bad `withtol` tolerance, `timerange(1,2)`, duration lag on irregular times, mixed time types in `synchronize` | all MATLAB-style errors | `test_errors_are_matlab_errors` |
| `istable(TT)` | MATLAB returns false | patched `istable` |
| Calendar steps, spline/pchip, table verbs returning plain tables | not covered | residual #755 |
