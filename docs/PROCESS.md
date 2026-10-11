# R&D process — iteration quality (OpenMATLAB)

Every iteration should be **high quality** by routing work through Issues,
Gherkin cases, pytest gates, and a Definition of Done — preferring
**off-the-shelf** tools.

Full QA layer model: [`QA.md`](QA.md). Defects: [`WORKFLOW.md`](WORKFLOW.md).

## Process loop (happy path)

```
1. Feature / gap Issue     (GitHub Issues + labels; optional Projects board)
2. Gherkin scenario        (features/*.feature — pytest-bdd)
3. Implement / stub        (src/openmatlab/… — still architecture-friendly)
4. Automated tests         (pytest unit + bdd smoke; CI on PR)
5. Update inventories      (test_catalog.yaml; feature_map.yaml sync note)
6. PR + review             (PR template QA checklist)
7. Merge when gates green  (branch protection — see below)
```

## Layer mapping (tools)

| Concern | Canonical tool | Repo support |
|---------|----------------|--------------|
| Features / work | **GitHub Issues** (+ optional **Projects**) | labels, issue templates |
| Capability inventory | Issues primary; **`docs/feature_map.yaml` optional sync/export** | `openmatlab features` |
| Behaviour cases | **Gherkin** + **pytest-bdd** | `features/*.feature`, `tests/bdd/` |
| Executable checks | **pytest** | `tests/unit`, markers |
| Environments | unit / conformance / interactive | `tests/` layout |
| Defects | **GitHub Issues** | `gh` / `openmatlab defects` |
| Gates | **GitHub Actions** | `docs/examples/ci.github-actions.yml` (copy to `.github/workflows/ci.yml`) |
| Coverage | **pytest-cov** | modest `fail_under` in pyproject |
| Future web UI | Playwright/Selenium | **not** until browser workbench exists |

## Features on GitHub (preferred)

### Labels (create once)

```bash
gh label create "bug" --color d73a4a --force
gh label create "gap" --color fef2c0 --force
gh label create "epic" --color 5319e7 --force
gh label create "chore" --color cfd3d7 --force
for L in host lang runtime numerics graphics libs qa docs; do
  gh label create "layer:$L" --color 0e8a16 --force
done
```

Optional: `feature:<id>` labels when useful (IDs from `docs/feature_map.yaml`).

### Projects (optional)

Use a GitHub **Project** board (e.g. columns: Backlog → Ready → In progress → Review → Done).
Card each Issue; do **not** invent a second in-repo ticket DB.

### `feature_map.yaml` role

- **Optional export / sync aid** for agents and offline inventory — **not** the
  work tracker.
- When an Issue closes or a capability lands, update the YAML status in the
  **same PR** (sync note, not a competing system).
- Dump: `openmatlab features`.

## Cases — Gherkin + pytest-bdd

- Specs live in `features/*.feature` (business-readable).
- Steps in `tests/bdd/` (pytest-bdd).
- Marker: `@pytest.mark.bdd` (and usually `@pytest.mark.unit` for smoke in CI).
- Catalog may link `impl:` to a bdd scenario node when useful (`docs/test_catalog.yaml`).

Prefer **pytest-bdd** (stays on pytest) over a separate Behave runner.

## Definition of Done (DoD)

An Issue / PR is done only if:

- [ ] Linked GitHub Issue exists (bug/gap/epic) with `layer:*` label
- [ ] Behaviour covered by Gherkin scenario **or** explicit waiver in PR
      (docs-only / chore)
- [ ] `pytest -m "unit or bdd"` green locally
- [ ] CI green on the PR
- [ ] `docs/test_catalog.yaml` updated if new cases; `docs/feature_map.yaml`
      status synced if capability changed
- [ ] No secrets committed; clean-room rules respected (no MATLAB RE)
- [ ] PR template QA checklist completed

## Branch protection (manual repo settings)

Recommended for `main` (Settings → Branches → Rule):

1. Require pull request before merging  
2. Require status check: **`CI / test`** (job name from Actions)  
3. Require conversation resolution  
4. Do not allow bypass without review (team size permitting)

Documented here because protection is configured in the GitHub UI, not in git.


## Enabling CI on GitHub

The workflow file lives at **`docs/examples/ci.github-actions.yml`** so agents
without the GitHub `workflow` OAuth scope can still push docs. To enable gates:

1. Copy to `.github/workflows/ci.yml` via the GitHub UI (Actions → New workflow)
   or a credential that has the `workflow` scope.
2. Turn on branch protection requiring check **`CI / test`**.

## Local commands

```bash
pip install -e ".[dev]"
openmatlab status
openmatlab features
openmatlab cases
pytest -m "unit or bdd" --cov=openmatlab --cov-fail-under=60
openmatlab test --suite unit
```
