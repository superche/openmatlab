# Epic #1033: ismissing, rmmissing, fillmissing

Milestone: M17 Analyst pipeline (parent epic #1032). Execution choice for the 2–3 fill methods: **constant**, **previous**, and **next**. #1039 corrects four review findings: a char blank is missing, empty inputs keep their shape, the `rmmissing` indicator follows the operating dimension, and a table variable fills down its rows.

## Problem

The analyst path washes a table or a numeric vector before `groupsummary`. `ismissing` already existed for strings and numeric NaNs, and it reported nothing missing for tables, categoricals, datetime, or cellstr. `rmmissing` and `fillmissing` did not exist.

## Design

`libs/missing_builtins.py` registers the three names on the shared builtin table, after the string module. The evaluator is unchanged.

Standard missing values are the ones this tree already uses: NaN for double, single, and duration; NaT for datetime; `None` for `<missing>` strings; code 0 for `<undefined>` categoricals; a blank (`' '`) for char; an empty character vector inside a cell. Integer and logical arrays have no missing value. A tab or any other non-blank character is present. A table or timetable is one column of that mask per variable. An empty array and a 0-row table come back with the same size from `ismissing`, `rmmissing`, and `fillmissing`.

`rmmissing` on a vector drops missing entries and keeps the vector's orientation. On a matrix it drops rows (or the dimension you pass) that contain at least `MinNumMissing` missing entries, default 1. On a table it drops those rows. `DataVariables` limits which variables count. The second output is a logical vector of the removed positions: a column when the operating dimension is 1, and a row when it is 2. A char array stays char. A char value stores its width in its rows, so a matrix whose every row was removed is a 0×0 empty char.

`fillmissing` walks the first dimension whose size is not 1, unless a dimension is given. Tables have no dimension argument; each variable is filled along its rows (dimension 1). That is also true of a one-row table, so a row-shaped variable is not filled across its columns. `'previous'` copies the last non-missing value forward and leaves a leading gap missing. `'next'` copies backward and leaves a trailing gap missing. `'constant'` requires a fill value: a scalar, a numeric vector with one value per non-operating slice, a single character when the array is char, or a cell array with one value per filled table variable. A char result stays char.

Any other method (`movmean`, `linear`, `nearest`, `spline`, `pchip`, `makima`, `movmedian`, `knn`, or a function handle) raises `OpenMATLAB:fillmissing:UnsupportedMethod` or `InvalidMethod`. `EndValues`, `SamplePoints`, and the other name-value options raise `UnsupportedOption`. The messages are `EvalError`s, so the CLI prints them without a Python traceback.

## Non-goals

The rest of the fill method matrix. `standardizeMissing`. Custom missing indicators on `ismissing`. Sparse matrices. `xlsx`. Corpus percentage and the Core backlog.
