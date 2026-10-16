# Epic #761 (M12 C-E1): sandboxed corpus runner

Milestone: [M12 Real-script compatibility gate](../milestones/M12-corpus-gate.md), criterion C02.

## Design

- `openmatlab.qa.corpus.runner.run_one(path, timeout, mode)` starts `python -m openmatlab.qa.corpus._child` per script. `run_many` runs them in parallel (one worker per CPU) and keeps input order.
- **Sandbox:** a fresh temporary work folder that is also `HOME`/`TMPDIR` (the script is copied in; its source folder is on the path so sibling functions resolve); `stdin=/dev/null`; a minimal environment with `MPLBACKEND=Agg` and no proxy variables; `setsid` plus `killpg` on timeout and after exit (reaps `system()` children); rlimits `RLIMIT_AS` 4 GiB, `RLIMIT_CPU` timeout+5 s, `RLIMIT_FSIZE` 16 MiB.
- **Output:** stdout/stderr go to files, not pipes, so memory stays bounded; 64 KiB of each is kept. A flood that hits the file limit is `error/output-limit`.
- **Verdict:** the child writes `{status, kind, error_id, message}` to a side file named by `OPENMATLAB_RESULT`, so printed text cannot forge a pass. No side file → `crash`. A Python traceback on stderr → `crash`.
- Statuses: `pass`, `error` (kinds `parse`, `eval`, `exit`, `output-limit`), `timeout`, `crash` (`internal`).
- **CLI:** `openmatlab run FILE... [--timeout S] [--json] [--parse-only]`. Exit code 0 pass, 1 error, 3 crash, 124 timeout, 2 missing file. Never a Python traceback.
- **Budget:** measured 50 pilot scripts in 13.3 s on 8 CPUs (~1.5 s start-up each), so a 300+ entry corpus fits well inside the 15-minute CI budget.

## Adversarial review

| Attack | Result |
|---|---|
| `while true, end` | `timeout`, process group killed; next script unaffected |
| Infinite `disp` | stopped by `RLIMIT_FSIZE` → `error/output-limit`; result stays < 70 KiB |
| Script prints a fake JSON pass | verdict comes from the side file → still `error` |
| `input()` | stdin closed → MATLAB end-of-input error, no hang |
| `zeros(1e6,1e4)` | bounded by `RLIMIT_AS`; reported as `crash` (engine raises a Python `MemoryError`; filed #781) |
| Unbounded recursion | reported as `error` with `MATLAB:recursionLimit` in the runner; engine fix tracked in #781 |
| Script writes files | they land in the throw-away sandbox folder, not next to the corpus |
| Network access | **not blocked at OS level** (environment only) → residual #780 |
