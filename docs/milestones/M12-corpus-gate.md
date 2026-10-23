# M12 — Real-script compatibility gate (corpus gate)

GitHub milestone: https://github.com/superche/openmatlab/milestone/12

**Related:**
- [M13 Graphics completion](M13-graphics.md) runs interleaved; the corpus `graphics` category ranks its epics.
- [M11 Debugger and Workbench](M11-debugger-workbench.md) (closed): manifest/strict-xfail model reused here.
- [`../GAP-ANALYSIS.md`](../GAP-ANALYSIS.md): missing-builtin counts from the corpus order the Core backlog (milestone/9).

## Intent

Use public, real MATLAB code as a measurable CI gate: a reproducible, licence-clean corpus, a sandboxed runner, tiered expected results, an automatic root-cause classifier and a dashboard. Failure groups drive the backlog instead of guesswork. Pilot (Rosetta Code, outside the repo): 11/15 = 73 % of de-noised runnable scripts pass; 22/22 function files parse.

Approved by Shaw on 2026-10-16. Decisions:
1. **Licensing.** GPL/GFDL sources (Rosetta Code, GNU Octave) are **downloaded at runtime and run locally only**; the repo stores only manifests (title/URL/revid/sha256) and results, **never the corpus code**. BSD/MIT sources may be vendored with their licence files. MathWorks code, docs, `.p` files and toolbox sources are never used.
2. **Thresholds** for C05–C08 are calibrated after the first full run and then locked in this document. **Locked 2026-10-16** (Epic #764), see [Threshold calibration](#threshold-calibration).
3. **Triage:** failure groups auto-file GitHub issues labelled `corpus`, deduplicated by `(category, key)`.
4. **CI:** the full corpus runs nightly; PRs run a sample.

## Exit criteria (measurable)

M12 is **done** only when **all** of these hold on `main`:

1. **Conformance.** Every criterion in [`tests/conformance/m12_manifest.py`](../../tests/conformance/m12_manifest.py) is `met`, and `pytest tests/conformance/test_m12_conformance.py` reports **0 xfail**.
2. **No open `p0` issue** on milestone/12.
3. **No Python traceback** reaches a user in the corpus run (C09).
4. **Docs.** No doc drift; CI on `main` is green; each epic has an accepted `docs/acceptance/EPIC-NNN.md`.

Tiers: **T0** parses; **T1** runs (exit 0, no error, no timeout); **T2** self-checks (`assert`, `%!assert`, bundled tests) pass; **T3** stdout matches a golden (transcript output, or Octave output only where MATLAB docs document the same behaviour, each with a doc link). Pass rates exclude `corpus-noise`; T1 also excludes `toolbox:*` and `io-env`.

**C03 noise rate** is measured on the Rosetta script blocks: the share that preprocessing passes on as runnable but whose run still fails for a sample reason (residual `corpus-noise`). Blocks that preprocessing sets aside up front (Octave/Scilab dialect, fragments that read undefined context) are de-noised: they are listed with a `dialect:`/`fragment:` note in `docs/corpus/results.json` and are not run. **C04** compares the top-level category (`toolbox:*` counts as `toolbox`) on `corpus/labels.json`.

## Criteria

| # | Criterion | Script | Priority | Epic | Status |
|---|-----------|--------|----------|------|--------|
| C01 | Corpus manifest ≥ 300 runnable entries from ≥ 4 sources, each with licence/URL/revid/sha256; CI licence allow-list; no GPL/GFDL code bodies in the repo | m12_c01_corpus_manifest | p0 | #762 | met (Epic #762; residual #785) |
| C02 | Runner: subprocess sandbox, timeout, stdin isolation, JSON results; one hang/crash does not affect others; full CI run ≤ 15 min | m12_c02_runner_isolation | p0 | #761 | met (Epic #761; residual #780) |
| C03 | Deterministic preprocessing (transcript de-prompting, function-file detection, `input` fixtures) with unit tests; pilot noise rate 46 % → ≤ 10 % | m12_c03_preprocess | p0 | #763 | met (Epic #763; residual #789) |
| C04 | Classifier: ≥ 90 % category accuracy on ≥ 60 hand-labelled failures; `internal-crash` recall 100 % | m12_c04_classifier | p0 | #763 | met (Epic #763; residual #789) |
| C05 | T0 parse pass rate ≥ 95 % (locked 2026-10-16 after the first full run: 87.5 %) | m12_c05_tier0 | p0 | #766 | met (Epic #766: endless functions, private and @class folders, parser gaps; full run T0 97.9 % (954/974)) |
| C06 | T1 run pass rate ≥ 65 % (locked 2026-10-16 after the first full run: 26.1 %) | m12_c06_tier1 | p0 | #766 | met (Epic #766 burn-down: full run on `3577e05` T1 67.6 % (456/675), T0 99.5 % (966/971), internal-crash 0; residuals: #797 timeouts; the cell paren-slice shape fix awaits Shaw) |
| C07 | T2 self-check pass rate ≥ 75 % (locked at the proposal value: no T2 oracle existed in the first full run; C-E5 #765 builds it) | m12_c07_tier2 | p1 | #765 | **met** (Epic #765, [design](../design/EPIC-765-oracles.md), [acceptance](../acceptance/EPIC-765.md); 2026-10-17: full run on `20145ad` (tree of `main` `2104b1c`) T2 82.3 % (3426/4161); 128 dialect-excluded Octave blocks are outside the rate, never passes (79.9 % if they were counted as failures); first run on `3567779` 64.1 %) |
| C08 | T3 golden pass rate ≥ 70 % (locked at the proposal value: no T3 oracle existed in the first full run; C-E5 #765 builds it); every Octave-sourced golden links MATLAB docs | m12_c08_tier3 | p1 | #765 | met (T3 75.3 % (55/73) on tip `5d9513a` full run; MATLAB-transcript goldens; Shaw 2026-10-17; [acceptance](../acceptance/EPIC-765.md)) |
| C09 | `internal-crash` = 0 in the full run | m12_c09_no_crash | p0 | #766 | met (Epic #766 PR: `*` width/precision in `sprintf`/`fprintf`, `display` inside functions; residual #838) |
| C10 | `REPORT.md` (docs corpus folder) generated; failure groups deduplicated and filed as `corpus` issues; pass→fail regression fails CI | m12_c10_report_triage | p1 | #764 | met (Epic #764; CI workflow install pending #833, residuals #832) |

## Threshold calibration

First full run: `docs/corpus/results.json` (1495 entries, timeout 20 s). [`REPORT.md`](../corpus/REPORT.md) is the dashboard.

| Tier | Proposal | First full run | Locked | Rationale |
|---|---|---|---|---|
| T0 | 98 % | 87.5 % (850/971) | **95 %** | The three largest parse groups (unterminated `function` files, NEWLINE and `end` tokens) cover about 93 of the 121 failures. Fixing them reaches about 97 %, which leaves a margin for long-tail syntax. |
| T1 | 85 % | 26.1 % (184/706) | **65 %** | 293 failures are a single engine gap (class-folder resolution, mostly chebfun) and 51 are `private/` resolution. Rosetta alone is already at 61.3 %. 85 % would need most of chebfun's numerical semantics to match exactly, which is beyond M12. |
| T2 | 75 % | no oracle yet (first T2 run on `3567779`: 64.1 % (2769/4319)) | **75 %** | Kept: there was nothing to calibrate against until C-E5 (#765); the threshold stays locked |
| T3 | 70 % | no oracle yet | **70 %** | Kept: same reason |

The thresholds are read by `openmatlab.qa.corpus.report.threshold()` from the criteria table above. Change them only with Shaw's approval.

## Epics (approved order, interleaved with M13)

1. **G-E0 #767** (M13, #760) first overall.
2. **C-E1 #761 (p0):** runner + `openmatlab run --json --timeout` + sandbox — C02.
3. **C-E2 #762 (p0):** corpus fetch, manifest, licence allow-list — C01.
4. **C-E3 #763 (p0):** preprocessing + classifier + labelled set — C03, C04.
5. **C-E4 #764 (p0):** REPORT dashboard, regression gate, deduplicated issue filing — C10.
6. Then M13 epics ranked by corpus graphics failure counts, with **C-E5 #765 (p1)** (T2/T3 oracles — C07, C08) and **C-E6 #766 (p0)** (burn-down — C05, C06, C09; seeds `findstr`, `strmatch`, `pascal`, paren-less `function`) interleaved by the highest-priority unmet criterion.

Absorbed: pilot findings seed C-E6. The Core backlog (milestone/9) is not moved; the corpus only ranks it.

## Non-goals

Byte-exact comparison with MATLAB output; making toolbox-dependent scripts pass (classified as `toolbox:*` only); committing copyleft corpus code; network-dependent scripts; GUI/App Designer/Simulink; pixel comparison (M13 G10).

## Progress snapshot

M12 opened 2026-10-16. **10 / 10** criteria met: C02 (Epic #761, [design](../design/EPIC-761-corpus-runner.md)), C01 (Epic #762, [design](../design/EPIC-762-corpus-manifest.md)), C03 and C04 (Epic #763, [design](../design/EPIC-763-preprocess-classifier.md)): residual noise 5.5 % (raw 43.8 %), classifier 92.0 % on 88 labelled failures, crash recall 100 %. C10 (Epic #764, [design](../design/EPIC-764-report-triage.md)): [REPORT](../corpus/REPORT.md) T0 87.5 %, T1 26.1 %; thresholds locked; 39 deduplicated `corpus` issues filed (#793-#831). C09 (Epic #766, rolling): the two internal crashes are fixed and a re-run shows internal-crash = 0 (T1 26.2 %). C05 (Epic #766 burn-down): endless functions, `private/` and `@class` folders and corpus parser gaps lift T0 to 97.9 % (954/974); T1 27.5 % (193/701). C06 burn-down (`verLessThan`/`ver`, cs-lists, `subsref` bypass, `@method` dispatch, `bsxfun`, `mat2cell`, logical `max`/`min`): T0 98.0 % (955/974), T1 37.2 % (256/688). General object arrays, `subsref` on call results, short logical masks, logical class kept by indexing, empties dropped in concatenation: T1 42.3 % (290/686). Logical masks in cell indexing and assignment growth, empty cells dropped in concatenation, `cellfun` keeping logical: T1 42.7 % (293/686). Pure-NumPy special functions (`gamma`, `erf`, Bessel, `airy`, `ellipj`), `perms`/`bitget`/`dec2base`/`toeplitz`/`peaks`, empty-colon assignment growth, `cellfun` legacy forms: T0 98.0 % (953/972), T1 46.5 % (315/678). Remaining T1 failures (363): 107 timeouts (interpreter speed: sampled timeouts still fail at 120 s), 153 semantics-diff (long tail; largest group 33 concatenation), 69 graphics plus graphics-property errors, 23 missing builtins, 19 parse errors. C06 met (2026-10-17): de-prompting bare Octave prompts and multi-line literals, Scilab `$` dialect, signature-only abstract-method implementations, exact-type evaluator fast paths, malformed `.m` structure reported as a MATLAB error (`MATLAB:m_invalid_file_structure`), corpus siblings limited to real function files: full run on `3577e05` T0 99.5 % (966/971), T1 67.6 % (456/675), internal-crash 0, no pass->fail regression against the previous baseline. Only C07 (T2) and C08 (T3) remain. C07: the T2 self-check oracle (#900) runs Octave `%!assert`/`%!test` blocks at run time (pass/fail, hashes and counts only; no Octave test source or expected values are committed) plus the chebfun and matlab2tikz own checks; burn-downs #901-#903 (statistics options, structure predicates, incomplete gamma/beta, `expint`, `gallery`) give a full run on `3567779` of T2 64.1 % (2769/4319), T0 99.5 % (966/971), T1 67.6 % (456/675), internal-crash 0, no pass->fail regression. Burn-downs #905-#908 (`interp1` rewrite, `mean`/`median`/`mode` options, `datestr` formats, `cov`/`var` per the documented syntax, `sinint`/`cosint`, signed zeros) give a full run on `b23f9b7` of T2 71.7 % (3097/4318), T0 99.5 % (966/971), T1 67.7 % (456/674); internal-crash 0 (the `fsum` overflow in `mean` on `chebfun/chebfun/test_range` found by the first attempt is fixed in this PR; that entry is a timeout, as in the baseline); the run shows 10 pass->fail block regressions in `interp1`, `num2str`, `median`, `mode` and `var`, which the next burn-down triages (fixed, or recorded as dialect exclusions where MATLAB's documented behaviour differs from Octave's). C07 met (2026-10-17): burn-downs #909-#911 (quadrature engine `quadgk`/`quadl`/`quadv`/`quad2d`/`integral2`/`integral3`, vector-valued and complex pp, `interpn`/`interp3`, `funm`/`logm` on a NumPy complex Schur form, moving-statistic weights and `SamplePoints`, `trapz`/`cumtrapz` forms, `strsplit` name-value prefixes) and dialect exclusions where documented MATLAB differs from Octave (`corpus/dialect.json`: block ids, hashes and our reasons only; outside the rate, never a pass) give a full run on `20145ad` (tree-identical to `main` `2104b1c`) of T2 82.3 % (3426/4161), T0 99.5 % (966/971), T1 68.0 % (458/674), internal-crash 0, no pass->fail regression against the `b23f9b7` baseline. C08 met (2026-10-23): T3 golden harness (`goldens.py`, #985) compares Rosetta script stdout to MATLAB `>>` transcripts (C03 deprompted); nondeterministic scripts have no golden; every T3 record is `golden:matlab` (Octave-produced goldens with MATLAB doc links are allowed per Shaw 2026-10-17 and remain available for burn-down). Full run on tip `5d9513a`: **T3 75.3 % (55/73)** against the locked 70 % threshold, T0 99.5 %, T1 70.5 %, T2 82.8 %, internal-crash 0. **M12 is 10 / 10**. Epic #765 stays open until Shaw accepts the docs/acceptance package. Residuals: T3 long tail (stdout mismatches + T1-driven failures) filed as `corpus` issues; #766/#797 burn-down continues where cheap.
