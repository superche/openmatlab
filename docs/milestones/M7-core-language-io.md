# M7 — MATLAB core language & I/O

GitHub milestone: https://github.com/superche/openmatlab/milestone/7

**Source:** [`docs/GAP-ANALYSIS.md`](../GAP-ANALYSIS.md), which covers its p0 rows plus selected p1 rows. These are base-MATLAB features that ordinary scripts need. Toolbox-like domain libraries belong to Domain toolboxes (milestone/3).

## Exit criteria (measurable)

M7 is **done** only when **all** of the following hold on `main`:

1. **Conformance suite green.** Every criterion in
   [`tests/conformance/m7_manifest.py`](../../tests/conformance/m7_manifest.py) has status
   `met`, and `pytest tests/conformance` reports **0 xfail** for M7 scripts
   (`tests/conformance/scripts/m7_*.m`, each with `*.expected.json` built from public
   MATLAB documentation semantics; each script asserts 15–35 behaviours, never a smoke line).
2. **No open `p0` Issue** on this milestone.
3. **No Python traceback** reaches the user for any M7 script or for the probes in
   `docs/GAP-ANALYSIS.md`. User-code failures surface as MATLAB-style errors.

Pending scripts run as **strict xfail**. Once a script passes, CI fails until the
manifest marks it `met`, which happens in the same PR that makes it pass.

## Criteria (priority order — epic selection MUST take the top unmet one)

| # | Criterion | Script | Priority | Epic | Issues | Status |
|---|-----------|--------|----------|------|--------|--------|
| C01 | Errors & exceptions: `try/catch [e]`, `error(msg)`, `error(id,fmt,...)`, `error(struct)`, `MException`/`throw`/`rethrow`, `assert`, `lasterr`, MATLAB ids on builtin errors | m7_c01_errors | p0 | #530 | #540 #541 | met (Epic #530; residual #565) |
| C02 | Functions: `nargin`/`nargout`, `varargin`/`varargout`, `narginchk`, `MATLAB:TooManyInputs`, local functions in scripts, `global`/`persistent`, `eval` (+catch), `feval`, `str2func`/`func2str`, `exist` | m7_c02_functions | p0 | #531 | #529 #542 #543 #544 | met (Epic #531; residual #569) |
| C03 | Command syntax and workspace commands: `clear` (names, wildcards), `exist(...,'var')`, `format`, `evalc`, `who`/`whos`, `pwd`/`cd ..`/`dir`, `which`, `help`, `clc`, `disp hello`, `isvarname` | m7_c03_command_syntax | p0 | #532 | #545 #546 | met (Epic #532; residual #573) |
| C04 | Formatted and file I/O: `fprintf` (fid and console, recycling), `fopen`/`fclose`/`fgetl`/`fgets`/`fscanf`/`fread`/`fwrite`, `fileread`, `delete`, `exist(f,'file')`, `save`/`load` (MAT, struct form, selection) | m7_c04_file_io | p0 | #533 | #547 #548 (#549 p1) | met (Epic #533; residual #577) |
| C05 | Core math: `fix rem sign hypot log2 diff cumprod gcd lcm primes factor isprime nchoosek factorial round(x,n)`, `median mode std var`, `rand randn randi rng randperm`, `tic toc pause` | m7_c05_core_math | p0 | #534 | #550 #551 #552 | met (Epic #534; residual #581) |
| C06 | Core arrays & sets: `repmat kron horzcat vertcat logspace meshgrid ndgrid cell2mat num2cell iscellstr`, `union intersect setdiff setxor ismember sortrows`, cellstr `unique`/sets, `'stable'` | m7_c06_arrays_sets | p0 | #535 | #553 #554 | met (Epic #535; residual #585) |
| C07 | Core strings: `strsplit strjoin strfind strcat strvcat str2num mat2str int2str dec2bin bin2dec hex2dec dec2hex blanks deblank` | m7_c07_strings | p0 | #536 | #555 (#556 p1) | met (Epic #536; residual #589) |
| C08 | Graphics core: figure/axes/line handles with `get`/`set`, `hold`, `subplot`, `title`/`xlabel`/`ylabel`/`legend`/`grid`/`axis`/`xlim`/`ylim`, `gca`/`gcf`, `close`, `saveas`, `bar`/`scatter`/`histogram` | m7_c08_graphics_core | p0 | #537 | #557 #558 (#559 p1) | met (Epic #537; residual #593) |
| C09 | Dense decompositions: `eig svd lu qr chol null orth trace cross dot`, `MATLAB:posdef` | m7_c09_linalg_decomp | p1 | #538 | #560 | met (Epic #538; residual #598) |
| C10 | `containers.Map` (handle semantics, KeyType) and date/time basics (`datetime`, `days`/`seconds`/`minutes`, `datenum`/`datestr`, `clock`, `weekday`) | m7_c10_map_datetime | p1 | #539 | #561 #562 | met (Epic #539; residual #602) |
| C11 | Caller/base workspaces and help browsing: `evalin` (`'base'`/`'caller'`, catch string), `assignin`, `doc`, `lookfor`, `what` (added 2026-10-13 after the user ruled #608 P0) | m7_c11_frames_help | p0 | #610 | #608 | met (Epic #610; residual #611) |

**First principles for scope:**
- `containers.Map` and `datetime` are in M7 because ordinary scripts use them for bookkeeping. Tables, timetables and categorical stay out: they are a data-analysis subsystem (GAP-ANALYSIS p2).
- Decompositions are base MATLAB, not a toolbox, so they belong here at p1.
- `classdef` gets its own milestone, because it is an object-system design.

## Progress snapshot

M7 opened 2026-10-13. #529 (local-function crash) fixed in PR #564.

**11 / 11** criteria met: C01 (Epic #530, errors & exceptions), C02 (Epic #531), C03 (Epic #532), C04 (Epic #533), C05 (Epic #534), C06 (Epic #535), C07 (Epic #536), C08 (Epic #537), C09 (Epic #538), C10 (Epic #539), C11 (Epic #610). Next: M7 close-readiness review (rerun).

## Close-readiness review (2026-10-13)

1. **Conformance.** All criteria are `met` (C01–C11 after Epic #610), and there are 0 M7 xfails on `main`.
2. **Open p0 issues.** You accepted and closed epics #530–#539. Epic #610 is open only for user acceptance. All p0 child issues are closed, and #606 (builtin argument leak) is fixed. You ruled #608 P0, and it was delivered as criterion C11 (Epic #610).
3. **No Python traceback.** A sweep of all GAP-ANALYSIS probes plus every builtin and intrinsic called with five malformed argument shapes showed 0 leaks after #606.

The GAP-ANALYSIS M7 rows, README and READY were updated in the same PR as this note.


## Close-out (2026-10-13)

**Status: closed.** You accepted every epic (#530–#539, #610), and the GitHub milestone is closed.

- **Criteria:** 11 / 11 met (C01–C11), with 0 xfails.
- **Open p0 issues:** none.
- **Traceback sweep:** 0 leaks after #606 and #615.
- **Doc drift:** the drift test passes.
- **`main` CI:** green.

**Residuals re-homed** (none remain on M7):

| Issue | Pri | Topic | New milestone |
|---|---|---|---|
| #565 | p2 | Error message text, MException.stack/getReport | [Core backlog](https://github.com/superche/openmatlab/milestone/9) |
| #569 | p1 | cellfun/arrayfun multi-input, nargin edge cases, inputParser/validateattributes (`evalin`/`assignin` done in #610) | [Core backlog](https://github.com/superche/openmatlab/milestone/9) |
| #573 | p2 | format modes, dir/ls layout, evalc in functions | [Core backlog](https://github.com/superche/openmatlab/milestone/9) |
| #577 | p2 | MAT v7.3, textscan breadth, encodings, readtable | [Core backlog](https://github.com/superche/openmatlab/milestone/9) |
| #585 | p2 | Arrays/sets edge cases | [Core backlog](https://github.com/superche/openmatlab/milestone/9) |
| #589 | p2 | Strings edge cases | [Core backlog](https://github.com/superche/openmatlab/milestone/9) |
| #598 | p2 | Linalg breadth (QZ, expm/logm, eigs/svds) | [Core backlog](https://github.com/superche/openmatlab/milestone/9) |
| #611 | p2 | Frames/help residual (dbstack/inputname, doc browser) | [Core backlog](https://github.com/superche/openmatlab/milestone/9) |
| #593 | p2 | Graphics: `h.Prop` dot notation, findobj, 3-D, colormap | [Object system](https://github.com/superche/openmatlab/milestone/8) (dot-notation needs the object model) |
| #602 | p2 | datetime/duration/Map breadth (calendarDuration, NaT, time zones) | [Object system](https://github.com/superche/openmatlab/milestone/8) |
| #581 | p2 | Core-math parity: stats/interp/optim options | [Domain toolboxes](https://github.com/superche/openmatlab/milestone/3) |
