# Epic #765 (M12 C-E5): T2 self-check and T3 golden oracles

Milestone: [M12 Real-script compatibility gate](../milestones/M12-corpus-gate.md), criteria C07 (T2 ≥ 75 %) and C08 (T3 ≥ 70 %).

## Design

`src/openmatlab/qa/corpus/oracles.py` adds the two oracles; `pipeline.py` writes `t2`/`t3` and a short `oracle` summary (counts and token positions only, never corpus text) into each record of `docs/corpus/results.json`. The unit is the corpus **entry**, as for T0/T1.

**T2 (self-check).**

- *chebfun self-tests.* The driver already runs `pass = test_x(); assert(all(pass(:)))`, so `t2` equals the driver outcome. The driver was not changed (T1 keeps its meaning).
- *GNU Octave `%!` tests* (401 function files, runtime-only, GPL, never committed). `octave_blocks()` splits the `%!` blocks; `%!assert` and `%!test` blocks are self-checks, with their `%!shared` set-up and `%!function` helpers. `%!error`/`%!warning`/`%!fail` (Octave error texts), `%!testif` (Octave build features), `%!xtest` (known Octave failures) and `%!demo` are not value self-checks and are skipped. Each block is translated deterministically: bug tags (`<*12345>`) dropped, escape-free double-quoted strings become char literals (they are char arrays in Octave), implicit line continuation inside `( )` gets `...`. A block that needs Octave-only syntax or functions (`#`, `!`, `++`/`+=`, `endfor`, chained assignment, `f(x)(2)`, `**`, `__internal__`, the explicit `OCTAVE_ONLY` list) is set aside, like the C03 dialect rule. Each block runs in `try`/`catch` against **OpenMATLAB's own** implementation of the function (the Octave file is never on the path), clears the non-shared variables first, and appends its verdict to a side file, so a timeout keeps the finished verdicts. A block OpenMATLAB cannot parse fails on its own; the others still run. The entry passes T2 only when **every** applicable block passes.
- Octave's `assert (observed, expected, tol)` is not MATLAB's `assert`, so blocks call `omt2_assert`, a clean-room MATLAB helper written for this project from the documented interface (condition form; class, size, NaN/Inf positions and values; `tol > 0` absolute, `tol < 0` relative; cells and structs recursively).
- Classification: the function under test missing is `missing-builtin:<name>`; an Octave-only function under test (`time`, `strftime`, `cstrcat`, `discrete_pdf`, ...) is `corpus-noise` `dialect:octave-only-function`; toolbox functions (`sinint`, `corr`, `rotx`, ...) are `toolbox:*`. An entry with no applicable block is `corpus-noise`.

**T3 (golden).** The golden is the command-window output its author pasted under MATLAB `>>` prompts (the transcript C03 de-prompting drops). Transcripts under Octave prompts are not goldens: M12 C08 requires MATLAB documentation evidence for every Octave-sourced golden, and Decision 1 forbids using MathWorks documentation as a source, so the set of Octave-sourced goldens is empty by construction. The normalisation is fixed in advance: whitespace and blank lines; `Columns N through M` wrap headers (terminal width); a sign separated from its number. Numbers compare with a relative tolerance of 1e-10, or, when both are printed with decimals at different precisions (the session's `format` is not in the code), at the coarser of the two precisions. Integer and exponent displays get no rounding. Display-style differences (cell or struct layout) are failures. Scripts whose output depends on the clock, the random generator, typed input or the host (`rand`, `date`, `tic`, `input`, `pwd`, ..., in the script or the page's staged functions) have no golden. A golden entry whose T1 run fails also fails T3.

## Adversarial review

| Attack | Result |
|---|---|
| Rate inflated by choosing the unit after seeing results | The unit (entry, all blocks must pass) was fixed before the first measurement and matches chebfun's `all(pass(:))` |
| Octave semantics counted as MATLAB | Octave-only syntax and functions are set aside by fixed rules; Octave behaviour that MATLAB does not share still runs and counts as a failure (conservative) |
| The Octave implementation passes its own tests | The Octave file is never staged; the test calls OpenMATLAB's function |
| A missing MATLAB function hidden as noise | The function under test is `missing-builtin` unless it is on the explicit Octave-only list |
| One unparseable block hides the rest | Blocks are parse-checked one by one; a parse failure fails only that block (and the entry) |
| A crash or `exit` in one block | Verdicts are appended per block; unfinished blocks fail the entry |
| Forged verdict lines | Only well-formed lines for known block numbers count, first verdict wins |
| Shared state leaks between tests | `clearvars -except <shared>` before every block |
| Lenient golden comparison | Rounding is forgiven only at the coarser printed precision with decimals on both sides; integer displays, exponents and layout are compared exactly |
| Random or clock output as golden | Nondeterministic scripts (including staged page functions) have no golden |
| Octave golden without MATLAB evidence | None used; a unit test asserts every T3 record is `golden:matlab` |
| Corpus text in the repo | Records keep counts, token positions and engine messages only; `check` still scans for copied bodies |
| Python traceback | Oracle failures are MATLAB errors inside the sandbox; C09 still requires internal-crash = 0 |

## Results

See [Results](#results-full-run) below, filled from the committed full run.
