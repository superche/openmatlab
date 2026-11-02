# Epic slice #1034: analyst story, writetable CSV, acceptance

Milestone: M17 Analyst pipeline (parent epic #1032). This is the last In item of that epic: the story a person can rerun, the `out/` export convention, and the acceptance package. It does not add a table verb.

## What already exists

`writetable` writes a table to delimited text (Epic #694), including categorical labels and empty fields for NaN. `readtable` `'TreatAsMissing'`, `ismissing` / `rmmissing` / `fillmissing` (`constant`, `previous`, `next`), and `groupsummary` `'IncludeEmptyGroups'` are already on this branch. The story only calls those.

## Story

`demos/analyst/assays.csv` is a 12-row synthetic moisture log (MIT, invented here). `demos/analyst/story_assays.m` reads it with `'TreatAsMissing', {'NA','-999',''}`, prints an `ismissing` count, drops rows with no site, fills temperature with `'previous'` and blank `qc` with `'constant','pass'`, drops rows that still have no moisture, casts `site` to a categorical that includes the unused category West, summarises with `'IncludeEmptyGroups', true`, and writes two CSV files.

West's mean is NaN and its `GroupCount` is 0. A real `qc` value `fail` is not overwritten. xlsx is not opened. `writematrix` is already documented for numeric matrices and is not called, because the result is a table.

## `out/`

`demos/analyst/out/README.md` is tracked and states the convention. `.gitignore` ignores every other file in that directory. The script `mkdir`s the directory when it is absent.

## Non-goals

xlsx. `detectImportOptions`. `fillmissing` methods other than `constant`, `previous`, and `next`. A fourth vertical. A corpus-percentage gate. Closing Core backlog issues. Editing an existing test.
