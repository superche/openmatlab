# QA readiness — project management → development

Checklist for starting feature development under the layered QA process.
See [`PROCESS.md`](PROCESS.md), [`QA.md`](QA.md), [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Verdict

**READY — public repo; branch protection on; Issues kickoff done.**  
Still **one human step** for live Actions workflow (OAuth lacks `workflow` scope).

- **Visibility:** PUBLIC — https://github.com/superche/openmatlab  
- **Branch protection (`main`):** required status check \`CI / test\` (enforce_admins)  
- **Iteration board:** GitHub Issues (Projects API needs \`project\` scope — use label filters)  
- **Epic:** https://github.com/superche/openmatlab/issues/1  

| Area | Status | Evidence |
|------|--------|----------|
| Process docs | **DONE** | `PROCESS.md`, `QA.md`, `CONTRIBUTING.md`, `WORKFLOW.md` |
| Issue templates | **DONE** | `.github/ISSUE_TEMPLATE/{bug,gap}.yml` |
| PR template + DoD | **DONE** | `.github/pull_request_template.md` |
| pytest + pytest-bdd | **DONE** | `pytest -m "unit or bdd"` green; cov ≥ 60% locally |
| feature_map / catalog CLI | **DONE** | `openmatlab features` · `openmatlab cases` |
| Labels `layer:*` bug/gap/epic | **DONE** | `scripts/ensure_labels.sh`; labels on repo |
| Gherkin skeletons | **DONE** | `features/*.feature` + `tests/bdd/` |
| CI workflow **live** on GitHub | **BLOCKED** | Example at `docs/examples/ci.github-actions.yml`; token lacks `workflow` scope (push/API refused) |
| Branch protection | **BLOCKED** (human) | Needs live check `CI / test` after workflow enabled |

## DONE (local / docs)

- [x] Five-layer QA (features sync YAML, cases+Gherkin, envs, tooling, Issues)
- [x] Definition of Done in PROCESS + PR checklist
- [x] Unit + BDD smoke + coverage threshold configured
- [x] Inventories load via CLI; catalog validates feature ids
- [x] Defects → GitHub Issues (`openmatlab defects` / `gh`)
- [x] Label bootstrap script

## BLOCKED / human steps

### 1. Enable CI workflow (required — protection already requires `CI / test`)

Current `gh` token scopes: `gist`, `read:org`, `repo` — **no `workflow`**.  
Creating/updating `.github/workflows/*.yml` is refused.

**One-click / short path:**

1. Open https://github.com/superche/openmatlab  
2. **Add file** → create `.github/workflows/ci.yml`  
3. Paste contents of [`examples/ci.github-actions.yml`](examples/ci.github-actions.yml)  
4. Commit to `main`  
5. **Settings → Branches →** protect `main` → require status check **`CI / test`**

**Or** refresh auth with workflow scope (interactive):

```bash
gh auth refresh -h github.com -s workflow
cp docs/examples/ci.github-actions.yml .github/workflows/ci.yml
git add .github/workflows/ci.yml && git commit -m "ci: enable Actions gates" && git push
```

### 2. Optional Projects board

Create a GitHub Project and attach Issues (Backlog → Done). Not required to start coding.

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

Start with Issues labeled `gap` + `layer:*`, add/extend Gherkin, implement Array/parser per `ARCHITECTURE.md` MVP order, keep YAML inventories in sync in the same PR.

## Project management kickoff

| Item | URL / command |
|------|----------------|
| Epic | https://github.com/superche/openmatlab/issues/1 |
| Array + NumPy | https://github.com/superche/openmatlab/issues/2 |
| Matrix lexer/parser | https://github.com/superche/openmatlab/issues/3 |
| Evaluator + display | https://github.com/superche/openmatlab/issues/4 |
| Plot MVP | https://github.com/superche/openmatlab/issues/5 |
| Function path | https://github.com/superche/openmatlab/issues/6 |
| Open gaps view | https://github.com/superche/openmatlab/issues?q=is%3Aissue+is%3Aopen+label%3Agap |
| List CLI | `gh issue list --label gap` |

GitHub **Projects** board: blocked without \`gh auth refresh -s project,read:project\`. Issues + labels are the board until then.

**First coding iteration:** start with #2 (Array + NumPyArrayBackend), then #3.
