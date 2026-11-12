# Calendar-width bins, datetime edges, several schemes (#1070)

Residual of #1053 / #1069. The four functions `groupsummary`, `groupcounts`, `grouptransform`, and `groupfilter` already share `_bin_columns`. This slice extends that one path. It does not fork a copy per function.

Read 2026-11-07, clean-room, from the public pages only:

- [groupsummary](https://www.mathworks.com/help/matlab/ref/double.groupsummary.html)
- [groupcounts](https://www.mathworks.com/help/matlab/ref/double.groupcounts.html)
- [grouptransform](https://www.mathworks.com/help/matlab/ref/double.grouptransform.html)
- [groupfilter](https://www.mathworks.com/help/matlab/ref/double.groupfilter.html)
- [discretize](https://www.mathworks.com/help/matlab/ref/double.discretize.html)
- [Perform Calculations by Group in Table](https://www.mathworks.com/help/matlab/matlab_prog/perform-calculations-by-group-in-table.html)

Those pages do not publish an error identifier for a bad bin scheme. Failures stay `EvalError` with the project id already used here, `MATLAB:<fn>:InvalidBins` or `MATLAB:<fn>:Unsupported`.

## What changed

**Named calendar widths.** `second`, `minute`, `hour`, `day`, `week`, `month`, `quarter`, `year`, `decade`, and `century` on a datetime. The bin edges are the starts of that unit from the unit that contains the earliest finite value through the first edge strictly after the latest. Weeks start on Sunday, the same rule `dateshift` already uses. There is no time zone in this project, so a calendar day is midnight to the next midnight; the daylight-saving sentence on the page has nothing to apply to.

The output column is `<unit>_<var>`, an ordinal categorical. Category names are the discretize `dur,'categorical'` formats: a year is `uuuu` (`2016`), a month is `MMM-uuuu` (`Jun-2016`), a quarter is `QQQ uuuu` (`Q4 2015`), a day is the default date (`28-Jan-2016`), an hour or finer unit is the default datetime, a week is `[24-Jan-2016, 30-Jan-2016)` (first day and last day), and a decade or century is `[2010, 2020)`. The last bin of an interval label uses `]`, matching `IncludedEdge,'left'` and the numeric bins shipped in #1053. `'IncludedEdge','right'` only changes which bin a shared edge falls in, and the brackets on interval labels.

On a duration the page allows `second`, `minute`, `hour`, `day`, and `year`. `year` is the fixed 365.2425-day year named on the discretize page, not a calendar year. The other four are fixed lengths. `week`, `month`, `quarter`, `decade`, and `century` stay datetime-only. Edges are multiples of that width anchored so the first edge is at or before the earliest finite value. Labels are duration intervals in the column's own display format (`[0 hr, 1 hr)`). The column name is still `<unit>_<var>`.

**A duration or calendarDuration width.** This is the separate "length of time" scheme, not the named unit. A duration width is a fixed step. Edges sit on multiples of that width, and the first multiple is the one at or before the earliest finite value. A width of one day therefore lands on midnights, and a width of one hour on clock hours, because those lengths divide the day. The label is still an interval (`disc_<var>`), not the point label of the named unit. A calendarDuration width is not a fixed grid: on a datetime it steps with this project's calendar addition, starting at the earliest finite value. That is why `calmonths(1)` is not the same call as `'month'`: `'month'` snaps to the first of the month, and `calmonths(1)` starts at the first timestamp. Adding months still clamps the day, so a width that starts on the 31st does not preserve the month end. On a duration, a calendarDuration has no calendar to step, so it becomes a fixed length: a year is 365.2425 days and a month is one twelfth of that. `calyears(1)` and `'year'` therefore bin a duration the same way. The column name is `disc_<var>`, the same prefix numeric edges already use, because the scheme has no unit name.

discretize refuses to build more than 65,536 bins and widens the step. The walk here does the same: it starts from an estimate and doubles the step if that cap would not reach the last value.

Each edge is computed from the first edge, not by adding the width onto the previous edge. Repeated addition drifts off a datetime or duration that was built in one product, and an exact boundary then falls into the next bin under `IncludedEdge`. Hour, minute, and second edges are rebuilt from the clock time with the same component formula as `datetime`. A duration width uses `(k0 + n) * width`, the same product a duration value stores. On a datetime, a duration width that is a whole number of seconds is rebuilt as that clock time too: `anchor + n * (1/24)` matches `datetime` only when the anchor is an exact midnight. Any other width still steps by `anchor + n * width` from the anchor.

**Datetime edges.** A datetime vector of two or more finite, strictly increasing values bins a datetime grouping variable. Labels are discretize intervals in the edges' display format, or the default format when the edges have none. A value outside the edges is `<undefined>`, the same missing group numeric edges already produce. The column is `disc_<var>`.

**Several schemes on one variable (R2024a).** The page says the bin argument and the grouping variables must be the same size, or one of them scalar. A scalar scheme still applies to every variable. A cell with one entry per variable is still one scheme each; an entry that is itself a cell is several schemes for that variable. One grouping variable and a cell of schemes is the same rule: every scheme applies to that variable. Each scheme adds its own grouping column, in the order given. A repeated name takes `_1`, `_2`, … from the helper the transform path already uses. Group numbers, empty groups, and missing keys are unchanged: the binned columns are ordinary grouping columns.

`'IncludedEdge'` without a bin argument is still an error. The #1053 probes that expect that stay as they are.

## Not in this slice

Timetable row times. `weekofmonth` and `weekofyear` (they were already outside the implemented `*of*` set). A bin count on a datetime. `pattern`, `vartype`, and function-handle grouping variables.
