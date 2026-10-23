# Epic #765 (M12 C-E5): T2 self-check oracle (T3 pending)

Milestone: [M12 Real-script compatibility gate](../milestones/M12-corpus-gate.md), criteria C07 (T2 ≥ 75 %, locked) and C08 (T3 ≥ 70 %, locked).

**Status:** C07 is **met** (T2 82.3 % → 82.7 % on tip). C08 is **met** (T3 75.3 % (55/73) on `7fa09df`; MATLAB-transcript goldens via `goldens.py`). Epic #765 stays open until Shaw accepts the acceptance package.

## Design (T2, as landed)

`src/openmatlab/qa/corpus/selfcheck.py` (PR #900) is the T2 oracle. The runner, preprocessing and classifier from C-E1..C-E4 are reused unchanged; `pipeline.py` writes a `t2` verdict per record into `docs/corpus/results.json`.

- **GNU Octave `%!assert` / `%!test` blocks** (GPL, pinned, downloaded at run time, never committed). Each block is one T2 record `octave/<dir>/<name>#<k>`. Only pass/fail, the block's sha256, counts, an error identifier and a redacted message (digits and quoted text removed) are kept. Block source and expected values are never written to the results.
- `%!shared` variables are set up once per group and passed into and out of each block, as Octave does; `%!function` helpers are staged as function files. `%!error`, `%!warning`, `%!testif`, `%!xtest`, `%!demo` and `%!fail` are counted as skipped (not value self-checks).
- Octave-only syntax inside a block is normalised to MATLAB at run time by `octave_to_matlab` (`#` comments, `!`/`!=`, `endif`-style keywords, `"..."` char strings, `x += y`, `printf`). Octave test vocabulary used inside test code (`NA`, `e`, `I`, `rows`, `columns`, `resize`, `fail`, the `assert` tolerance form) comes from small own shims in `selfcheck`'s `t2lib/` folder. They are on the harness path only, never on a user's path.
- Tests run against **OpenMATLAB's own** implementation of the function under test. The Octave `.m` file is never staged.
- **chebfun** `tests/` (BSD-3-Clause): the driver asserts `all(pass(:))` on the test's own result vector, so T2 = T1 for `selftest` entries. **matlab2tikz** ACID scenes (BSD-2-Clause): the scene's own status, so T2 = T1 for `acid-scene` entries.
- **Exclusions** follow the T1 model (`report.excluded`): tests of Octave-only functions (`OCTAVE_ONLY`) are `toolbox:octave-only`, toolbox functions are `toolbox:*`, environment functions are `io-env`. **Dialect exclusions** (`corpus/dialect.json`, PR #910) list Octave blocks whose expected behaviour differs from documented MATLAB behaviour (for example, `interp1` extrapolation defaults). Only block ids, sha256 hashes and our own reasons are stored. An exclusion applies only while the block's hash matches. Excluded blocks are outside the rate and never count as a pass.

## Burn-down (feature PRs)

| PRs | Scope |
|---|---|
| #901-#903 | `datevec`, `tensorprod`, `normalize`, structure predicates, `mode`/`var` outputs, single-class propagation, incomplete gamma/beta, `expint`, `betaln`, `gallery` |
| #905-#908 | `interp1` rewrite, `mean`/`median`/`mode` options, `datestr` formats, `cov`/`var` per the documented syntax, `sinint`/`cosint`, signed zeros |
| #909 | `mean` `fsum` overflow fix (an internal crash found by a full run) |
| #910-#911 | quadrature engine (`quadgk`/`quadl`/`quadv`/`quad2d`/`integral2`/`integral3`), vector-valued and complex pp, `shiftdim`, `interpn`/`interp3`, `interp2` cubic methods, `funm`/`logm` on a NumPy complex Schur form, moving-statistic weights and `SamplePoints`, `trapz`/`cumtrapz` forms, `strsplit` name-value prefixes, dialect exclusions |

Full runs: #904 (`3567779`, 64.1 %), #909 (`b23f9b7`, 71.7 %), #913 (`20145ad`, **82.3 %**).

## Adversarial review

| Attack | Result |
|---|---|
| The rate is inflated by dropping failing blocks | Exclusions are fixed by rule (Octave-only function list, toolbox list, env list) or listed one by one in `dialect.json` with a reason against documented MATLAB behaviour. They are outside the rate and never a pass. If the 128 dialect-excluded blocks were counted as failures, T2 would be 79.9 %, still above 75 %. |
| A dialect exclusion silently covers a changed block | An exclusion matches by block id **and** sha256; an edited upstream block runs again. |
| The Octave implementation passes its own tests | The Octave file is never staged; the block calls OpenMATLAB's function. |
| Octave assert semantics are counted as MATLAB | `t2_assert` is a clean-room shim from the documented interface (condition form; class, size, NaN positions, values; absolute and relative tolerance), on the harness path only. |
| Shared state leaks between blocks | Only `%!shared` variables are carried between blocks of a group, as in Octave. |
| A crash or timeout in one block hides the rest | Each block is its own record; a timeout fails only that block. |
| Corpus text in the repo | Records keep hashes, counts, identifiers and redacted messages only; `corpus check` still scans for copied bodies (C01). |
| Pass→fail regressions are hidden | `python -m openmatlab.qa.corpus gate` compares against the committed baseline; the #913 run has no pass→fail regression against `b23f9b7`. |
| Python traceback | Block failures are MATLAB errors inside the sandbox; C09 still requires internal-crash = 0 (0 in the #913 run). |

## Residuals

- **C08 (T3 goldens):** met at 75.3 %. Optional burn-down: Octave-runtime goldens with doc links; stdout-mismatch residuals.
- The T2 long tail (276 `assert-mismatch`, 74 undefined functions, ...) is tracked through the deduplicated `corpus` issues and the #766 burn-down.

## C08 (T3) — in progress (Shaw 2026-10-17)

Shaw approved (2026-10-17, "都按照matlab文档来"): T3 goldens may be (1) MATLAB transcripts under
\`>>\` prompts, and (2) Octave-produced stdout at run time when each golden links public MATLAB
docs confirming the behaviour. Store hashes / pass-fail / counts only; never commit GPL corpus
or expected values. Where Octave differs from documented MATLAB, record a dialect exclusion
(never a pass).

\`src/openmatlab/qa/corpus/goldens.py\` implements the shared match/normalisation and the
MATLAB-transcript source. Pipeline wires T3 for Rosetta script entries with a deprompted
MATLAB transcript that is not nondeterministic. Octave-runtime goldens (with doc URLs) are
the next burn-down step under this epic.

