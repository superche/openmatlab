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
2. **Thresholds** for C05–C08 are calibrated after the first full run and then locked in this document (table below shows the proposal values until then).
3. **Triage:** failure groups auto-file GitHub issues labelled `corpus`, deduplicated by `(category, key)`.
4. **CI:** the full corpus runs nightly; PRs run a sample.

## Exit criteria (measurable)

M12 is **done** only when **all** of these hold on `main`:

1. **Conformance.** Every criterion in [`tests/conformance/m12_manifest.py`](../../tests/conformance/m12_manifest.py) is `met`, and `pytest tests/conformance/test_m12_conformance.py` reports **0 xfail**.
2. **No open `p0` issue** on milestone/12.
3. **No Python traceback** reaches a user in the corpus run (C09).
4. **Docs.** No doc drift; CI on `main` is green; each epic has an accepted `docs/acceptance/EPIC-NNN.md`.

Tiers: **T0** parses; **T1** runs (exit 0, no error, no timeout); **T2** self-checks (`assert`, `%!assert`, bundled tests) pass; **T3** stdout matches a golden (transcript output, or Octave output only where MATLAB docs document the same behaviour, each with a doc link). Pass rates exclude `corpus-noise`; T1 also excludes `toolbox:*` and `io-env`.

## Criteria

| # | Criterion | Script | Priority | Epic | Status |
|---|-----------|--------|----------|------|--------|
| C01 | Corpus manifest ≥ 300 runnable entries from ≥ 4 sources, each with licence/URL/revid/sha256; CI licence allow-list; no GPL/GFDL code bodies in the repo | m12_c01_corpus_manifest | p0 | #762 | met (Epic #762; residual #785) |
| C02 | Runner: subprocess sandbox, timeout, stdin isolation, JSON results; one hang/crash does not affect others; full CI run ≤ 15 min | m12_c02_runner_isolation | p0 | #761 | met (Epic #761; residual #780) |
| C03 | Deterministic preprocessing (transcript de-prompting, function-file detection, `input` fixtures) with unit tests; pilot noise rate 46 % → ≤ 10 % | m12_c03_preprocess | p0 | #763 | pending |
| C04 | Classifier: ≥ 90 % category accuracy on ≥ 60 hand-labelled failures; `internal-crash` recall 100 % | m12_c04_classifier | p0 | #763 | pending |
| C05 | T0 parse pass rate ≥ 98 % (proposal; locked after first full run) | m12_c05_tier0 | p0 | #766 | pending |
| C06 | T1 run pass rate ≥ 85 % (proposal; locked after first full run) | m12_c06_tier1 | p0 | #766 | pending |
| C07 | T2 self-check pass rate ≥ 75 % (proposal; locked after first full run) | m12_c07_tier2 | p1 | #765 | pending |
| C08 | T3 golden pass rate ≥ 70 % (proposal; locked after first full run); every Octave-sourced golden links MATLAB docs | m12_c08_tier3 | p1 | #765 | pending |
| C09 | `internal-crash` = 0 in the full run | m12_c09_no_crash | p0 | #766 | pending |
| C10 | `REPORT.md` (docs corpus folder) generated; failure groups deduplicated and filed as `corpus` issues; pass→fail regression fails CI | m12_c10_report_triage | p1 | #764 | pending |

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

M12 opened 2026-10-16. **2 / 10** criteria met: C02 (Epic #761, [design](../design/EPIC-761-corpus-runner.md)), C01 (Epic #762, [design](../design/EPIC-762-corpus-manifest.md)). Next: C-E3 #763 preprocessing and classifier.
