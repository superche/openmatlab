# Epic delivery scripts

These scripts automate the M7 epic flow: feature PR → green CI → squash merge → acceptance package → evidence-tip sync → close the child issues and comment on the epic. Run them from a clean checkout with `gh` authenticated and `.venv` present.

| Script | Usage | What it does |
|---|---|---|
| `ship.sh` | `ship.sh "<title>" "<body>"` | Runs the unit, bdd and conformance tests (stops if any fail), commits, pushes, opens the PR, then calls `land.sh`. |
| `land.sh` | `land.sh <PR>` | Updates the branch if it is behind `main`, waits for CI, and squash-merges. Exits non-zero if CI fails. |
| `epicdocs.py` | see the docstring | Flips the manifest criterion to met and updates the M7 doc, `feature_map.yaml` and `test_catalog.yaml`. |
| `accept.py` | `accept.py <config.json>` | Writes `docs/acceptance/EPIC-N.md` (live demos plus test runs) on a `docs/N-acceptance` branch. |
| `sync.sh` | `sync.sh <EPIC> <ACC_PR>` | Records the acceptance PR's squash SHA as the evidence tip. |
| `finish.sh` | `finish.sh <EPIC> <FEAT_PR> <ACC_PR> <SYNC_PR> <CHILD>...` | Closes the child issues and comments on the epic. Refuses to run unless all three PRs exist and are MERGED. |
| `epic_close.sh` | `epic_close.sh <EPIC> <FEAT_PR> <CHILD>...` | Runs accept → ship → sync → finish with `set -euo pipefail`. Every step is gated on the previous PR having actually merged. The config is read from `$EPIC_CONFIG` (default `/tmp/c<EPIC>.json`). |

The gates exist because of an incident in Epic #536: a follow-up step ran after an acceptance PR's tests failed, because a `| tail` pipe hid the exit code. Never pipe these scripts' output without `set -o pipefail`.
