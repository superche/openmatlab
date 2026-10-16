# Epic #764 (M12 C-E4): corpus REPORT dashboard, regression gate, deduplicated issue filing

Milestone: [M12 Real-script compatibility gate](../milestones/M12-corpus-gate.md), criterion C10.

## Design

- `src/openmatlab/qa/corpus/report.py` computes tier pass rates. `corpus-noise` is excluded everywhere, and `toolbox:*`/`io-env` are excluded from T1-T3. It also provides `regressions(new, previous)` (pass -> not pass, for ids present in both runs), `render()` (which writes [`docs/corpus/REPORT.md`](../corpus/REPORT.md)), `load_results()` for C05-C09, and `threshold(tier)`, which reads the locked thresholds from the M12 criteria table.
- `src/openmatlab/qa/corpus/triage.py` groups failures by `(category, key)`. `file_issues()` opens one issue labelled `corpus` per new group, with `p0` added for `internal-crash`. Dedup uses a body marker `<!-- corpus-group: category|key -->` that is searched across open **and closed** issues, so a group is filed once ever. Filing is opt-in, has a minimum group size (internal-crash is always filed) and a per-run cap.
- CLI: `python -m openmatlab.qa.corpus report | gate <results> [--baseline] | triage [--file]`. Errors print one line with no traceback.
- `.github/workflows/corpus.yml` fetches the corpus at runtime (it is never committed). PRs run a 1-in-10 sample and the full corpus runs nightly. Each run publishes a report artifact, and a pass->fail regression against the committed `docs/corpus/results.json` fails the job. The nightly run files new groups.
- Thresholds were calibrated on the first full run and are locked in the M12 doc: T0 95 %, T1 65 %, T2 75 %, T3 70 %.

## Adversarial review

| Attack | Result |
|---|---|
| Same root cause filed many times | Marker dedup across all issue states; unit and BDD tests file twice and get one issue |
| A closed issue's group reappears | Not re-filed (the marker is found); a reopen is a human decision |
| An entry removed from the corpus looks like a regression | Only ids present in both runs are compared |
| A sample run compared against the full baseline | Regressions are checked per id, so the sample compares a subset |
| Rates inflated by excluding failures | Only `corpus-noise` (all tiers) and `toolbox`/`io-env` (T1+) are excluded, as the M12 doc specifies |
| REPORT.md drifts from results | A unit test re-renders it and compares |
| Issue spam on the first run | `--min 2` and `--limit 50`; dry run by default |
| Missing results file / gh failure | One-line error, exit 1, no traceback |
| Timeouts on a slower CI runner flap the gate | Residual (filed) |
