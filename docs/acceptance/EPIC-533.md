# Acceptance evidence: Epic #533 (formatted and file I/O, save/load)

**Epic:** [#533](https://github.com/superche/openmatlab/issues/533)  
**Feature PR:** [#578](https://github.com/superche/openmatlab/pull/578) (#547, #548, #549)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-533-file-io.md`](../design/EPIC-533-file-io.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `c5e61ac148106d09736740a5d003585324b25035` | Squash merge of feature PR [#578](https://github.com/superche/openmatlab/pull/578) |
| Evidence merge tip | `61740c97da90bd1f11c19f44ac3e7081d7897a78` | Squash merge of [#579](https://github.com/superche/openmatlab/pull/579); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M7 criterion C04 is **met**. Epic #533 stays **open** until the user accepts it.

All of these now work:
- **Formatted output:** `fprintf` to the console or a fid; a statement call prints with no `ans`.
- **Low-level I/O:** `fopen`/`fclose`, `fgetl`/`fgets`, `fscanf`/`sscanf` (MATLAB's cyclic scanner), `fread`/`fwrite` precisions, `fileread`, `delete`, `tempname`, and the file-system helpers.
- **save/load:** a NumPy-only MAT Level 5 codec. It covers numeric, int, single, complex, logical, char, cell, struct and sparse, plus compressed reads, `-append`, `-struct`, wildcards, load into a struct, and ASCII files.
- **Text tables:** `readmatrix`/`writematrix`, `dlmread`, `csvread`/`csvwrite` and `textscan`.

Interop was checked against scipy's MAT implementation in a throw-away venv. The scipy-written fixtures in `tests/fixtures/mat/` keep CI honest without scipy.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| fprintf + low-level file I/O (fopen..fwrite, fileread, delete, tempname, paths) | #547 | [#578](https://github.com/superche/openmatlab/pull/578) | [job 115138966612](https://github.com/superche/openmatlab/actions/runs/38349677472/job/115138966612) **success** |
| save/load MAT v5 (classes, compressed read, -append/-struct, load to struct, ASCII) | #548 | [#578](https://github.com/superche/openmatlab/pull/578) | same job |
| textscan, dlmread/csvread, readmatrix/writematrix, csvwrite/dlmwrite | #549 | [#578](https://github.com/superche/openmatlab/pull/578) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "f = [tempname '.txt']; fid = fopen(f, 'w'); n = fprintf(fid, '%d,%d\n', [1 2; 3 4]), fclose(fid); t = fileread(f)"
n =

8

t =

1,3
2,4
$ openmatlab -e "fprintf('%5.1f|', [1.26 2]); fprintf('\n')"
  1.3|  2.0|
$ openmatlab -e "x = sscanf('1.5,2.5,3', '%f,')'"
x =

   1.5000   2.5000   3.0000
$ openmatlab -e "m = [tempname '.mat']; s.a = {1, 'two'}; X = int8([1 -2]); save(m, 's', 'X'); clear s X; load(m); class(X), s.a{2}"
ans =

int8

ans =

two
$ openmatlab -e "S = load('tests/fixtures/mat/scipy_v5_compressed.mat'); S.s"
ans =

  struct with fields:

    f: [1 2]
    g: 'txt'
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1212 passed, 2 deselected, 6 xfailed in 16.10s
$ pytest tests/unit/test_file_io.py tests/bdd/test_file_io_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C04-m7_c04_file_io]" --tb=no
29 passed in 0.52s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
5 passed, 6 xfailed in 0.48s
```

New cases: 23 unit tests (`tests/unit/test_file_io.py`), 5 Gherkin scenarios (`features/file_io.feature`), 2 committed third-party MAT fixtures, and conformance `m7_c04_file_io` (21 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.file_io
libs.file_io                     libs       done     fprintf, file I/O, save/load (MAT v5), text tables
```

## Residuals (filed)

- [#577](https://github.com/superche/openmatlab/issues/577) (p2): MAT v7.3/objects/strings, textscan breadth, encodings, readtable, save -ascii options. `isnan` was found missing; that is tracked under C05 (#534).

## Milestone progress (M7)

- Criteria met: **4 / 10** (C01–C04)
- Conformance scripts passing: **4 / 10** (strict xfail pending: C05–C10)
- Next: Epic #534 (C05 core math)
