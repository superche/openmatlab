# Analyst exports

`demos/analyst/story_assays.m` writes CSV here:

- `site_summary.csv` — `groupsummary` of the washed assay log, including the empty West group
- `cleaned.csv` — the table after `rmmissing` / `fillmissing`, before the summary

Those files are generated and gitignored. This README is the only tracked file in the directory, so the convention has a place in the tree. Do not commit the CSV.
