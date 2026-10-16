# QA readiness — project management → development

Checklist for starting feature development under the layered QA process.
See [`PROCESS.md`](PROCESS.md), [`QA.md`](QA.md), [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Verdict

**READY — public repo; CI live; branch protection on.** Milestones 1/2/3/4/5/6/7/8/10/11 closed (M10 Tables and M11 Debugger closed 2026-10-16; M3 Domain toolboxes and M8 Object system closed 2026-10-16; M7 closed 2026-10-13). Open: Core backlog.

- **Visibility:** PUBLIC — https://github.com/superche/openmatlab
- **CI:** `.github/workflows/ci.yml` active; required check `test` green on `main`
- **Branch protection (`main`):** required status check `test` (enforce_admins)
- **Iteration board:** GitHub Issues (Projects API needs `project` scope — use label filters)
- **Closed epics:** all epics through #349 / #371 / #372 (see `gh issue list --label epic --state closed`)
- **Acceptance:** `docs/acceptance/EPIC-*.md` (one per epic)

| Area | Status | Evidence |
|------|--------|----------|
| Process docs | **DONE** | `PROCESS.md`, `QA.md`, `CONTRIBUTING.md`, `WORKFLOW.md` |
| Issue templates | **DONE** | `.github/ISSUE_TEMPLATE/{bug,gap}.yml` |
| PR template + DoD | **DONE** | `.github/pull_request_template.md` |
| pytest + pytest-bdd | **DONE** | `pytest -m "unit or bdd"` green; cov ≥ 60% locally |
| feature_map / catalog CLI | **DONE** | `openmatlab features` · `openmatlab cases` |
| Labels `layer:*` bug/gap/epic | **DONE** | `scripts/ensure_labels.sh`; labels on repo |
| Gherkin skeletons | **DONE** | `features/*.feature` + `tests/bdd/` |
| CI workflow **live** on GitHub | **DONE** | `.github/workflows/ci.yml`; Actions workflow **CI** active |
| Branch protection | **DONE** | `main` requires check `test` (enforce_admins) |

## DONE (local / docs)

- [x] Five-layer QA (features sync YAML, cases+Gherkin, envs, tooling, Issues)
- [x] Definition of Done in PROCESS + PR checklist
- [x] Epic Done requires `docs/acceptance/EPIC-NNN.md` (see PROCESS § Epic acceptance)
- [x] After-epic docs/feature_map sync chore required before next epic (PROCESS)
- [x] Unit + BDD smoke + coverage threshold configured
- [x] Inventories load via CLI; catalog validates feature ids
- [x] Defects → GitHub Issues (`openmatlab defects` / `gh`)
- [x] Label bootstrap script
- [x] Live Actions CI + protected `main`

## Optional / human steps

### 1. Optional Projects board

Create a GitHub Project and attach Issues (Backlog → Done). Not required to start coding.
`gh` still lacks `project` / `read:project` scope if you want CLI board management.

## Smoke commands (dev machine)

```bash
pip install -e ".[dev]"
./scripts/ensure_labels.sh          # idempotent
openmatlab status
openmatlab features
openmatlab cases --status active
pytest -m "unit or bdd" --cov=openmatlab --cov-fail-under=60
```

## Next phase entry

M7, M8 and M3 are closed. M7 close-out: `docs/milestones/M7-core-language-io.md`. M8 close-out (10/10, epics #618–#624 accepted 2026-10-16): `docs/milestones/M8-object-system.md`. M3 close-out (7/7, epics #625–#631 accepted 2026-10-16): `docs/milestones/M3-domain-toolboxes.md`. p2 residuals remain on the closed M3/M8 milestones. Open roadmap: [Core backlog](https://github.com/superche/openmatlab/milestone/9). M10 Tables and M11 Debugger closed 2026-10-16 (see `docs/milestones/M10-tables.md`, `docs/milestones/M11-debugger-workbench.md`); p2 residuals remain on those closed milestones.

| Item | URL / command |
|------|----------------|
| Open gaps view | https://github.com/superche/openmatlab/issues?q=is%3Aissue+is%3Aopen+label%3Agap |
| List CLI | `gh issue list --label gap` |
| Acceptance | `docs/acceptance/EPIC-*.md` |

GitHub **Projects** board: optional; needs `gh auth refresh -s project,read:project`. Issues + labels are the board until then.
