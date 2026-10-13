# Design: Epic #539, containers.Map and date/time basics (M7 C10)

Covers #561 (containers.Map) and #562 (datetime/duration basics: datetime, year/month/day, days/seconds/minutes, datenum/datestr, clock, weekday).

## First principles
- **A small object protocol** (`runtime/objects.py`). Values with `is_object` implement `index`, `assign`, `get_prop`, `binop` and `display_text`. The evaluator dispatches to them in five places: binary operators, `obj(args)`, `obj(args) = v`, `obj.Prop` / `obj.method(...)`, and display. `containers.Map(...)` is resolved when `containers` is not a variable. This is one generic hook, not special cases scattered through the evaluator.
- **containers.Map is a handle.** Assignment copies the reference, so `m4 = m; m4(k) = v` changes `m` (MATLAB). Keys come back sorted (char by code, numeric ascending). `KeyType`/`ValueType` are inferred or given, mismatches error with `MATLAB:Containers:TypeMismatch`, and a missing key errors with `MATLAB:Containers:Map:NoKey`. `length`/`isempty`/`numel`/`size` follow MATLAB (`numel` is 1).
- **datetime is a value type** stored as MATLAB datenum days. Component overflow carries (month 13 is January of the next year; Jan 31 + 1 day is Feb 1). Seconds are rounded to 0.1 ms on output, because a datenum near 7e5 is only accurate to about 1e-5 s. Without that, 13:05:00 would show as 13:04:59.
- **Arithmetic** (MATLAB rules): datetime ± duration or number → datetime; datetime − datetime → duration; duration ± duration and duration × number → duration; duration ÷ duration → double. datetime + datetime and duration − datetime error. Comparisons work within a type, and datetime also compares with date text.
- **datenum/datestr/weekday.** `datenum(y,mo,d,…)` matches MATLAB (2020-01-01 is 737791). datestr supports the symbolic tokens and common numeric formats. weekday counts Sunday as 1.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| Handle aliasing through a copy | Shared. Covered by a test. |
| Missing key; wrong key or value type; key/value count mismatch | MATLAB errors. Covered by a test. |
| Month/day rollover, leap February | Correct (29 days in Feb 2020). Covered by a test. |
| Float truncation in time-of-day display | Fixed with rounding. Covered by a test. |
| datetime + datetime | Error. Covered by a test. |
| `m.keys()` method syntax, `m.Bogus` | Method works; unknown name errors. Probed. |

## Residuals
#602.
