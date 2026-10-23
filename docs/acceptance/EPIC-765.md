# Acceptance evidence: Epic #765 (C-E5 T2 self-check + T3 golden oracles)

**Epic:** [#765](https://github.com/superche/openmatlab/issues/765)  
**Feature PRs:** #900-#911 (T2 harness and burn-downs); [#913](https://github.com/superche/openmatlab/pull/913) (C07 met); [#984](https://github.com/superche/openmatlab/pull/984) (corpus re-run); [#985](https://github.com/superche/openmatlab/pull/985) (T3 harness); [#986](https://github.com/superche/openmatlab/pull/986) (C08 met)  
**Milestone:** [Real-script compatibility gate (M12)](https://github.com/superche/openmatlab/milestone/12) · [`docs/milestones/M12-corpus-gate.md`](../milestones/M12-corpus-gate.md)  
**Design + adversarial review:** [`docs/design/EPIC-765-oracles.md`](../design/EPIC-765-oracles.md)  
**Captured:** 2026-10-23 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `5d9513a4974fde8fa54340fcf11c21b57defcc11` | Squash merge of C08-met PR [#986](https://github.com/superche/openmatlab/pull/986) (on tip of #985 T3 harness) |
| Evidence merge tip | `8fd7d93c8853a852db1bf92520868deabb11a8f7` | Squash merge of [#989](https://github.com/superche/openmatlab/pull/989); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M12 criteria **C07** (T2 self-check ≥ 75 %) and **C08** (T3 golden ≥ 70 %) are both **met**. Epic #765 stays **open** until Shaw accepts this package.

- **C07:** T2 oracle runs GNU Octave `%!assert`/`%!test` blocks at run time (pass/fail, hashes and counts only; no Octave source or expected values committed), plus chebfun and matlab2tikz own checks. Dialect exclusions where documented MATLAB differs from Octave are outside the rate (never a pass). Full run on tip: **T2 82.8 % (3442/4159)**.
- **C08:** T3 golden harness (`goldens.py`, #985) matches Rosetta script stdout to MATLAB `>>` transcripts (C03 deprompted). Nondeterministic scripts have no golden. Every T3 record is `golden:matlab` (Shaw 2026-10-17 also allows Octave-produced goldens with MATLAB doc links for further burn-down). Full run on tip `5d9513a4974f`: **T3 75.3 % (55/73)** against the locked 70 % threshold.
- Companion tiers on the same full run: T0 99.5 % (966/971), T1 70.5 % (474/672), internal-crash 0, no pass→fail regression vs the #984/#986 overlay baseline.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| T2 self-check harness | #765 | [#900](https://github.com/superche/openmatlab/pull/900) | success (see prior acceptance) |
| T2 burn-downs + C07 met (82.3 %) | #765 | [#901](https://github.com/superche/openmatlab/pull/901)–[#913](https://github.com/superche/openmatlab/pull/913) | success |
| Full corpus re-run on 48bb627 (T0/T1/T2; T3 n/a) | #765 | [#984](https://github.com/superche/openmatlab/pull/984) | success |
| T3 golden harness (`goldens.py` + pipeline) | #765 | [#985](https://github.com/superche/openmatlab/pull/985) | [job 120216162774](https://github.com/superche/openmatlab/actions/runs/39892778961/job/120216162774) **success** |
| C08 met: T3 75.3 %; M12 10/10 | #765 | [#986](https://github.com/superche/openmatlab/pull/986) | [job 120219077949](https://github.com/superche/openmatlab/actions/runs/39893692239/job/120219077949) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "disp(abs(quadgk(@(x) exp(-x.^2), -Inf, Inf)^2 - pi) < 1e-10); A = [1 2; 0 3]; disp(norm(funm(A, @exp) - expm(A)) < 1e-10)"
1
1
$ openmatlab features | rg -F qa.corpus_tier
qa.corpus_tier2                  qa         done     Corpus T2 self-check oracle and dialect exclusions
qa.corpus_tier3                  qa         done     Corpus T3 golden oracle (MATLAB transcripts + Octave-runtime with doc links)
```

## Measurable gate: pytest

```text
$ pytest tests/unit/test_corpus_goldens.py tests/unit/test_corpus_selfcheck.py \
    "tests/conformance/test_m12_conformance.py::test_m12_criterion[C07-m12_c07_tier2]" \
    "tests/conformance/test_m12_conformance.py::test_m12_criterion[C08-m12_c08_tier3]" --tb=no
52 passed in 0.58s
$ pytest tests/conformance/test_m12_conformance.py --tb=no
11 passed in 3.66s
$ pytest -m "unit or bdd" --ignore=tests/unit/extensions/test_community_signal_package.py --tb=no
2211 passed, 2 skipped, 37 deselected in 107.37s
```

(Local box lacks `tkinter`; CI `test` job on #986 includes the desktop extension module and is green. One local desktop CLI case also needs tkinter.)

New cases: `tests/unit/test_corpus_goldens.py` (T3 match, source, nondeterminism, integrity); C08 conformance flipped to met in #986.

**Existing tests changed: none** (Shaw-approved MATLAB-docs test fixes for cell/colormap/TickLabels/saveas landed separately in #982).


## Window recording (E2E) — M12 corpus gate

- Video: [`demos/corpus/showcase_m12_corpus.mp4`](../../demos/corpus/showcase_m12_corpus.mp4) (~71s, 1920×1200)
- Also copied to `/workspace/recordings/showcase_m12_corpus.mp4`
- Helper: `demos/corpus/record_m12_corpus_showcase.sh` (ffmpeg x11grab + fullscreen xfce4-terminal, DejaVu Sans Mono 18)
- Batch note: [`M12-M13-batch.md`](M12-M13-batch.md) · Chinese summary: `/workspace/proposals/M12-M13-acceptance-evidence.md`

| t (approx) | Scene |
|---|---|
| 0–4 s | Title card: M12 Corpus Gate / Epic #765 / C07+C08 |
| 4–22 s | `sed -n '1,25p' docs/corpus/REPORT.md` — T0 99.5 %, T1 70.5 %, T2 82.8 %, **T3 75.3 % (C08)** |
| 22–30 s | Show deprompted T3 sample source `demos/corpus/samples/t3_Boolean_values_1.m` |
| 30–42 s | `openmatlab run` Boolean_values/1 (real T3 golden; passes) |
| 42–55 s | `openmatlab run` Sum_and_product_of_an_array/1 (real T3 golden; passes) |
| 55–71 s | `pytest tests/conformance/test_m12_conformance.py` → **11 passed**; wrap-up |

```bash
DISPLAY=:2 ./demos/corpus/record_m12_corpus_showcase.sh
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| T3 stdout-mismatch (8 entries) | [#987](https://github.com/superche/openmatlab/issues/987) |
| T3 blocked by T1 failure (19 entries) | [#988](https://github.com/superche/openmatlab/issues/988) |
| T2 long tail / burn-down | #766 (rolling) |
| Interpreter timeouts | #797 |

## Milestone progress (M12)

- Criteria met: **10 / 10** (C01–C10)
- Conformance scripts passing: **11 / 11** (C08 no longer xfail)
- Next: Shaw watches `showcase_m12_corpus.mp4` + reads this package; cheap #766/#797 burn-down; do **not** close #765 or the M12 milestone until Shaw accepts.
