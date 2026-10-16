# Epic #763 (M12 C-E3): corpus preprocessing and failure classifier

Milestone: [M12 Real-script compatibility gate](../milestones/M12-corpus-gate.md), criteria C03 and C04.

## Design

- `src/openmatlab/qa/corpus/preprocess.py`: deterministic transforms with no network and no clock. They de-prompt transcripts (`>>` code is kept and the echoed output is saved as `transcript` for the T3 oracle), strip echo pasted without prompts, detect function files (parse-only at T0, not run at T1), supply fixtures for `input`/`keyboard`, and detect free reads (identifiers that nothing in the file or engine defines, which marks a fragment as noise).
- `src/openmatlab/qa/corpus/classify.py`: a rule-based classifier with these categories: `internal-crash`, `timeout`, `corpus-noise`, `toolbox:<tb>`, `io-env`, `graphics`, `missing-builtin`, `parse-error`, `semantics-diff`. It uses only error ids, message patterns and name lists. It is deterministic and uses no LLM. `corpus-noise` is excluded from every pass rate. `toolbox`/`io-env` are excluded from T1.
- `src/openmatlab/qa/corpus/pipeline.py`: runs preprocess -> sandboxed run (C02 runner) -> classify. It writes `docs/corpus/results.json`, which holds ids, tiers, category, key and an error message capped at 240 chars. No corpus code is stored.
- `corpus/labels.json`: hand labels for the classifier accuracy criterion.

## Results (full run, results.json)

- Residual noise on the Rosetta script set: **5.5 %** (raw 43.8 %).
- Classifier accuracy: **92.0 %** on 88 labelled failures. Crash recall: **100 %**.

## Adversarial review

| Attack | Result |
|---|---|
| Copyleft code leaks into committed results | Records hold ids/categories/keys and only engine error messages (capped); no source text |
| Preprocessing hides real failures as noise | Noise needs a positive rule (dialect function, free read, prose); residual noise is measured |
| Classifier non-determinism | Pure rules; the same input always gives the same category (unit tests) |
| Internal crash misfiled as semantics | Traceback/Python exception rules run first; crash recall is 100 % on labels |
| `input()` blocks a run | Fixtures plus spare answers; the timeout is still enforced by the runner |
