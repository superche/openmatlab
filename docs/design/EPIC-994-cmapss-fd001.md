# Epic #994 (V-E1): C-MAPSS runtime download and FD001 load

Milestone: [M14 C-MAPSS PHM vertical](../milestones/M14-cmapss-vertical.md), criteria V01 and V02.

## Problem

A PHM script starts by downloading NASA C-MAPSS and reading `train_FD001.txt`. The file is space-padded, has no header, and has 26 columns (unit, cycle, 3 operational settings, 21 sensors). The zip must not enter the repository.

`readtable` already accepts `'Delimiter',' '` (runs of spaces collapse) and `'ReadVariableNames',false` with `'VariableNames'`. `readmatrix` did not: a space delimiter kept empty fields between padding spaces. That is the only reader change in this epic.

## Design

- **Manifest.** `demos/cmapss/manifest.json` is metadata only: Zenodo URL, DOI 10.5281/zenodo.15346912, CC BY 4.0, byte size, sha256, PHM08 column names, and the public FD001 row counts. No zip and no sensor text.
- **Fetch.** `libs/cmapss.py` (`python -m openmatlab.libs.cmapss fetch`, or MATLAB `cmapss_fetch`) writes `downloads/cmapss/CMAPSSData.zip`, checks size and sha256, and extracts only `train_FD001.txt`, `test_FD001.txt`, and `RUL_FD001.txt` into `downloads/cmapss/fd001/`. Zip members are stored by basename, so a `../` member cannot leave that directory. `$OPENMATLAB_CMAPSS_CACHE` overrides the cache root. A matching zip is not downloaded again.
- **Names.** `cmapss_names` returns the 26 manifest names. The upstream readme calls column 26 "sensor measurement 26"; that column is `sensor_21`.
- **Loader.** `demos/cmapss/load_fd001.m` is the call a MATLAB user would write: `readtable(..., 'Delimiter',' ', 'ReadVariableNames',false, 'VariableNames', names)`. `'rul'` uses one column named `rul`. An unknown split errors before any download.
- **Story stub.** `demos/cmapss/story_fd001.m` fetches (or reuses the cache) and prints train height, width, unique units, and the cycle count of unit 1.
- **readmatrix.** `'Delimiter',' '` and `'Delimiter','space'` collapse whitespace, matching `readtable`. `readmatrix(file)` with no delimiter already fell through to whitespace splitting.

Citation recorded in the module, the loader, and the demo: A. Saxena, K. Goebel, D. Simon, and N. Eklund, PHM08, 2008; DOI 10.5281/zenodo.15346912.

## Non-goals

FD002–FD004 as an exit criterion. The full `detectImportOptions` matrix (still #721). Preprocessing, metrics, `heatmap`, and export (V-E2…V-E6).

## Adversarial review

| Attack | Result |
|---|---|
| Zip of the wrong size or sha256 | `RuntimeError` from `verify_zip`; a failed download is deleted and retried |
| Zip member `../evil.txt` or `train_FD002.txt` | Not written. Only the three FD001 basenames are extracted |
| `load_fd001('nope')` | `OpenMATLAB:cmapss:BadSplit` before `cmapss_fetch` |
| Space-padded row with a trailing run of spaces | `readtable` and `readmatrix(...,'Delimiter','space')` both return 26 columns |
| Cache path | `git check-ignore` reports the existing `downloads/` rule; `downloads/cmapss/` restates the M14 policy. `git ls-files` does not list the zip or the txt |
| Existing tests | Not modified |
