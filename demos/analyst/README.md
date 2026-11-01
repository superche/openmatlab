# Analyst field-assay story

A synthetic bench log an analyst can wash and summarise. The rows are invented for this demo and ship with the repository (MIT). There is no third-party dataset and no spreadsheet.

```bash
openmatlab -e "run('demos/analyst/story_assays.m')"
```

`assays.csv` is a 12-row moisture log. Tokens `NA`, `-999`, and a blank field are missing (`readtable` `'TreatAsMissing'`). Two bottles have no site. Two temperatures are blank. Two moisture readings are sensor faults. Two `qc` marks were left empty; one real mark is `fail` and must stay `fail`.

`story_assays.m` then:

1. Prints an `ismissing` count per column (9 missing cells).
2. `rmmissing` drops the two rows with no site.
3. `fillmissing(..., 'previous')` carries the last temperature down the file. The sheet is ordered by site and each site's first kept row already has a temperature, so the carry does not cross sites. `'next'` is implemented and is not used here. Other fill methods are out of scope.
4. `fillmissing(..., 'constant', 'pass')` fills the empty `qc` marks only.
5. `rmmissing` drops the three rows that still have no moisture. Moisture is not imputed.
6. Turns `site` into a categorical whose categories are North, South, East, and West. West was planned and has no rows.
7. `groupsummary(..., {'mean','sum'}, ..., 'IncludeEmptyGroups', true)` keeps West: count 0, sums 0, means NaN.
8. `writetable` writes the summary and the cleaned rows to CSV.

`writematrix` already writes a numeric matrix to delimited text. This result is a table, so the story calls `writetable`. xlsx is not a path: `readtable` / `writetable` still reject spreadsheets.

## `out/` convention

Generated CSV belongs in `demos/analyst/out/`. The script creates that directory if it is missing. `out/README.md` is the tracked note that states the convention. Every other file under `out/` is gitignored (see `.gitignore`). Do not commit `site_summary.csv` or `cleaned.csv`.

The Workbench recording is `demos/workbench/showcase_m17_analyst.mp4` after a capture. Re-record with `DISPLAY=:2 ./demos/analyst/record_story_assays.sh`. Without a display, `./demos/analyst/record_story_assays.sh --headless` reruns the story and writes no mp4.
