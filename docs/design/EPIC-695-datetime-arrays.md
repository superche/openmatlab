# Epic #695 (T-E5): datetime/duration array completion

Milestone: [M10 Tables and data types](../milestones/M10-tables.md), criterion T09 (absorbs the datetime subset of #602 without time zones, and the datetime part of #673).

## Design

- **Arrays.** `datetime`/`duration` keep their existing storage (a 2-D float array of datenums or days). They gain `'`/`.'` transpose, 2-D and column-preserving indexed assignment (`t(2) = …`, `t(r,c) = …`, growth pads with NaT), and concatenation (`libs/datetime_arrays.concat`, called from the evaluator's matrix builder). In concatenation, date text converts to datetime and `[]` is skipped. A duration promotes to calendarDuration. Any other mix is a MATLAB error.
- **NaT.** `NaT`, `NaT(n)`, `NaT(m,n)`, `'Format'`. NaT propagates through components (NaN), arithmetic, `dateshift` and `between`.
- **Formats.** `'InputFormat'` parses through a Unicode-pattern → `strptime` translation (`yyyy MM M dd d HH hh mm ss SSS a EEE 'literal'`). When `'Format'` is omitted, `Format` defaults to the InputFormat. Char, string and cellstr arrays give same-shaped datetime arrays, and `''`/`'NaT'` give NaT. Display, `char`, `string` and `cellstr` use one formatter (`objects.java_format`). The default format is `dd-MMM-yyyy`, or `dd-MMM-yyyy HH:mm:ss` when any element has a time of day, as in MATLAB, so every element of an array shows in the same format. `t.Format = …` is settable. `'TimeZone'` raises a clear "not supported" error.
- **Component assignment.** `t.Year/Month/Day/Hour/Minute/Second = v` (scalar or same size) recomputes through `datenum_from_parts`, so overflow rolls over: Month 14 → February of the next year, Day 32 → the next month, Month 0 → December of the year before.
- **calendarDuration** (`runtime/calendar_duration.py`). Stores months, days and time as same-shaped arrays. `calyears/calquarters/calmonths/calweeks/caldays` (integers only) and `calendarDuration(y,mo,d[,h,mi,s | t])` construct it. Adding it to a datetime applies months first and clamps the day to the month's end (31-Jan + 1 month = 29-Feb-2020), then days, then time. It supports `+`/`-` with calendarDuration, duration and numbers (days), integer `*`, and `==`/`~=`. Relational comparison is an error, as in MATLAB. Display looks like `1y 2mo 3d 4h 30m`.
- **between(t1,t2[,components])** walks whole calendar units, using the smallest requested month unit (months, quarters or years), then whole days or weeks, then time. Negative spans are mirrored. **split(calD, units)** returns the integer parts, largest unit first, and `'time'` comes back as a duration. `split(duration, units)` is also added.
- **dateshift(t,'start'|'end',unit[,rule])** supports year, quarter, month, week (starting Sunday), day, hour, minute and second. The rule can be `current`/`next`/`previous` or an integer n. For 'end', the result is the start of the unit's last day (year/quarter/month/week).

## Adversarial review

- **Probe sweep** (`tests/unit/test_datetime_arrays.py::test_errors_are_matlab_errors`): bad InputFormat text, non-text InputFormat, TimeZone, mixed datetime/duration concat, duration with a number, bad dateshift where/unit/rule, non-datetime `between`, bad components, non-integer calendar units, relational comparison of calendarDurations, a non-integer multiplier, calendarDuration minus datetime, `split` without units, a bad duration unit, a malformed `calendarDuration(...)`, non-numeric or mis-sized component assignment, and a non-text Format. All raise MATLAB errors with no Python traceback.
- **Column assignment bug found and fixed.** The old `_TimeBase.assign` always reshaped to a row, so `t(2) = x` turned a column into a row.
- **Display change.** Arrays now use one format for every element. Previously each element chose its own format, which MATLAB never does. The full suite was unchanged by this.
- **No existing test was changed.**
- **Deferred (residual #733):** `dateshift(...,'end','day'|'hour'|...)` and `'dayofweek'` rules, time zones (#602), `calendarDuration` `Format`, `datetime` `'ConvertFrom'`, locale-dependent month names, `caldiff`, and the duration display precision for non-integer days.
