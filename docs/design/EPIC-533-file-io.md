# Design: Epic #533, formatted and file I/O, save/load (M7 C04)

Covers #547 (fprintf and low-level file I/O), #548 (save/load .mat) and #549 (text tables, p1).

## First principles
- **One file table.** `fid` maps to an open binary Python file. 1 and 2 are stdout and stderr. New fids start at 3 and take the lowest free number.
  - Text goes through Latin-1, so every byte round-trips: `fwrite` then `fgetl` is lossless.
  - `fopen` failure returns `-1` plus a message and never raises, as in MATLAB.
- **fprintf shares sprintf's formatter.** It uses `text_builtins._format`: format cycling, escapes, `%%`. `fprintf(fid, ...)` is chosen when the first argument is numeric.
  - A statement call prints and does not bind `ans`, because `fprintf` is a statement-zero intrinsic. `n = fprintf(...)` returns the byte count.
  - Handles (`@fprintf`) go through the plain builtin.
- **scanf is one scanner** (`_scan`), shared by `sscanf` and `fscanf`. It follows MATLAB's rules:
  - the format is applied cyclically until the first mismatch;
  - blanks in the format match any run of whitespace, and numeric and `%s` conversions skip leading whitespace;
  - `%*` skips a value, widths are honoured, and `Inf`/`NaN` are accepted;
  - an all-`%s`/`%c` format yields char;
  - the size argument is `n`, `Inf`, `[m n]` or `[m Inf]`, column-major and zero-padded.
  - `fscanf` repositions the file just after the consumed text.
- **fread/fwrite precisions.** These include `uint8` (the default), `int16`…`uint64`, `single`/`double`, `char`, plus the `*T` and `T=>U` output-class forms. Writes saturate integers to the class range, as MATLAB does. Data is little-endian.
- **MAT v5 codec with NumPy only** (`libs/mat5.py`), written from the public MathWorks MAT-File Format document.
  - **Writer:** an uncompressed Level 5 file. It has a 128-byte header (`MATLAB 5.0 MAT-file`, version 0x0100, `IM`) and one `miMATRIX` element per variable.
  - **Supported classes:** double, single, int8..uint64 (real and complex), logical (uint8 data with the logical flag) and char (UTF-16 code units, column-major, multi-row). Cell and struct work recursively, including struct arrays. Sparse is written as `ir`/`jc`/`pr` with O(nnz) memory.
  - **Reader:** handles the same set, plus `miCOMPRESSED` (zlib; MATLAB's default), small-element tags, big-endian (`MI`) files and `miUTF8` char.
  - **Rejected with an error:** string arrays (they need MAT objects), MException, and v7.3 HDF5.
- **save/load are frame intrinsics.** They need the caller's workspace.
  - Supported forms: `save(f)`, `save(f, vars...)` with wildcards, `-append`, `-struct s [fields]` and `-ascii`. A missing `.mat` extension is added.
  - `load(f)` assigns into the caller's workspace and `S = load(f, ...)` returns a struct. A non-MAT numeric text file loads as a matrix named after the file.
- **Text tables.**
  - `readmatrix` detects the delimiter and skips header lines; empty fields become NaN.
  - `dlmread`/`csvread` treat empty fields as 0 and take row and column offsets.
  - `writematrix` uses `%.15g`. `csvwrite`/`dlmwrite` use `%.5g` (MATLAB documents five significant digits).
  - `textscan` returns a 1×K cell: numeric column vectors, and cell columns for `%s`/`%q`.

## Interop validation (not a dependency)
In a throw-away venv (`/tmp/sv`, not part of the project) I checked against scipy 1.x:
- `scipy.io.loadmat` reads every class that `save` writes: int16, logical, single, complex, char, multi-row char, sparse, struct array and nested cell.
- `load` reads `scipy.io.savemat` output, both compressed and plain.

Those two scipy files are committed as fixtures (`tests/fixtures/mat/`), so CI checks the compressed-read path without scipy.

## Adversarial review (done before PR)
| Attack | Result |
|---|---|
| `fprintf('x')` as a statement displays `ans = 1` | Statement-zero intrinsic. Covered by `test_fprintf_statement_prints_without_ans`. |
| `fprintf(fid, ...)` with a closed or unknown fid | `Invalid file identifier` with id `MATLAB:FileIO:InvalidFid`. |
| A matrix argument printed in row-major order | Column-major flattening via `_flat_args`. Covered by a test (`1-3|2-4|`). |
| `sscanf` over-reads past a mismatch, or `fscanf` loses the file position | Stops at the mismatch; the position is restored to the consumed bytes. |
| `fwrite` with out-of-range values | Saturates (`300→255`, `-5→0` for uint8). Covered by a test. |
| MAT char matrices transposed, or struct arrays flattened | Column-major char grid; struct `elems` in column-major order with all fields per element. Round-trip test and scipy check. |
| Empty arrays and sizes (`zeros(0,3)`) | The dims are kept. Covered by a test. |
| MATLAB-written compressed files | zlib element path. Covered by the fixture test. |
| `save` of a missing variable, or of string arrays | MATLAB-style errors. Covered by tests. |
| `load` of a missing file | `MATLAB:load:couldNotReadFile`. |
| Gaps | v7.3, objects, the breadth of textscan options, encodings and readtable are filed as **577**. `isnan` (C05) was found missing, noted, and is covered by Epic #534. |
