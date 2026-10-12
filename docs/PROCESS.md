# R&D process — iteration quality (OpenMATLAB)

Every iteration should be **high quality** by routing work through Issues,
Gherkin cases, pytest gates, and a Definition of Done — preferring
**off-the-shelf** tools.

Readiness: [`READY.md`](READY.md).

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



## Work tracking — GitHub Issues only (mandatory)

**All** actionable work items (features, gaps, bugs, chores, residuals, milestone
follow-ups, and any other todos) **must** be managed as **GitHub Issues** on this
repository.

Disallowed as the system of record:

- Agent-local todo lists / scratch checklists that never become Issues
- Docs-only todo sections that are not mirrored by Issues
- In-chat task lists without corresponding Issues

Docs (`PROCESS`, `ARCHITECTURE`, `EPIC-NNN`, milestone pages) may **summarize**
or **link** Issues; they do not replace them. When an agent discovers work, it
opens or updates an Issue (with labels + milestone) before or as it acts.

## Milestones (roadmap)

Track multi-epic roadmaps with **GitHub Milestones** (not a second tracker).

States on 2026-10-12: milestone/1, /4, /5, /6 **closed**; /2 **open** (exit met, backlog); /3 **reserved**.

| Milestone | Intent |
|-----------|--------|
| **Workbench MVP** | Foundation REPL/scripts/control (epics #1 #19 #33) — closed when accepted |
| **Octave-breadth language & numerics** | Language + numeric core toward MATLAB/Octave parity (builtins, cells, assign, control flow, indexing) |
| **Plugin host (VS Code–style)** | Published plugin contract + host for **community** plugins (not MathWorks proprietary). Doc: [`milestones/M-plugins.md`](milestones/M-plugins.md); contract: [`design/PLUGIN-CONTRACT.md`](design/PLUGIN-CONTRACT.md) |
| **Domain business-conformance** | Reference vectors / tests for plugin domains (`hamming` etc.). Doc: [`milestones/M-domain-conformance.md`](milestones/M-domain-conformance.md); GitHub milestone/5 |
| **MATLAB-aligned Workbench** | Host product: command window, editor, workspace browser, current folder, figure mgmt via plugin slots. Doc: [`milestones/M-workbench-aligned.md`](milestones/M-workbench-aligned.md); GitHub milestone/6 |
| **Domain toolboxes** | Rich domain libraries / heavier graphics beyond core parity (prefer community plugins on the host contract; after conformance gate) |

**Rules**

1. Every **epic** Issue must be assigned to exactly one milestone at open (or in the after-epic sync).
2. **Residual Issues** filed at epic acceptance inherit the **same milestone** as their parent epic unless they clearly belong to a later roadmap (e.g. domain toolbox → Domain toolboxes).
3. After user accepts an epic: close the epic Issue; keep residuals on the milestone until delivered or re-homed.
4. Agents use `gh api` / `gh issue edit --milestone "..."` (closed milestones: PATCH `milestone=<number>`).
5. Do not invent parallel roadmap docs that duplicate milestone membership — link milestone URLs from `ARCHITECTURE.md` / acceptance packages when useful.


### Milestone exit criteria & epic selection (mandatory)

- Each active milestone has `docs/milestones/M<N>-*.md` with **measurable exit criteria**:
  a conformance manifest where applicable (`tests/conformance/m2_manifest.py` for
  M2; `tests/conformance/domain_manifest.py` for Domain business-conformance),
  required feature_ids at `done`/`partial` per the milestone doc, and no open
  `p0` on the milestone.
- Open Issues on a milestone carry exactly one priority label: `p0` / `p1` / `p2`.
- **Epic selection:** the next epic MUST target the highest-priority **unmet**
  criterion in the milestone doc (p0 before p1, then table order) — not convenience.
- Unmet criteria scripts run as **strict xfail**; when an epic makes one pass, the
  same PR flips it to `met` and updates the milestone doc table.
- New gaps discovered by conformance get an Issue + priority label + milestone.

### EPIC-NNN.md — Milestone progress section (mandatory)

Every acceptance package includes:

```
## Milestone progress (M<N>)
- Criteria met: X / Y
- Conformance scripts passing: X / Y (xfail pending: …)
- Remaining gaps (priority order): Cxx #issue …
```

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
- [ ] **Epics only:** acceptance evidence `docs/acceptance/EPIC-NNN.md` + Issue comment (see below)

## Epic acceptance (mandatory)

Closing an **epic** Issue requires an acceptance-evidence artifact, not only
child Issues closed and CI green.

### Artifact

- Path: `docs/acceptance/EPIC-NNN.md` (NNN = epic number, zero-padded)
- Must include **measurable** checks with **pasted real command output**
  (CLI demos, `pytest -m "unit or bdd"` summary, `feature_map` statuses,
  PR/CI URLs, tip SHA). Do **not** invent transcript text.
- Land via PR; required check **`test`** must pass; merge to `main`.
- Comment on the epic Issue with a link to the evidence file on `main`
  (e.g. `docs/acceptance/EPIC-001.md`).
- **Tip SHAs:** record both (1) **functional tip** — last commit where ordered
  acceptance code landed; (2) **evidence merge tip** — commit that merged
  `EPIC-NNN.md` onto `main`. Re-run instructions for the doc itself should
  checkout the evidence tip (or `main`), not only the functional tip.

### DoD addendum (epics)

In addition to the Issue/PR DoD above:

- [ ] `docs/acceptance/EPIC-NNN.md` merged
- [ ] Epic Issue comment links the evidence
- [ ] Residual / non-goals explicitly listed if MVP is intentionally partial

Example: [`acceptance/EPIC-001.md`](acceptance/EPIC-001.md).


## Residual Issues (mandatory)

Every epic acceptance package **must** file GitHub Issues for residual /
non-goal items called out in that epic’s `docs/acceptance/EPIC-NNN.md`
(and any “known gap” called incomplete in the conditional-pass notes).

Rules:

1. One Issue per coherent residual (or a small tightly-related cluster).
2. Labels: `gap` (or `chore` if docs-only); layer label; body links **parent epic**.
3. Comment on the epic with a table of residual Issue URLs when filing.
4. EPIC-NNN.md may summarize residuals, but **Issues are canonical** for
   tracking — prose-only residuals are not enough.
5. Residuals already owned by a later epic board may link that epic instead
   of duplicating a gap Issue.


## Plugins (community extension host)

OpenMATLAB uses a **VS Code–style** plugin host: manifest `contributes`, host
**slots**, activation events, Extension Host API, and SemVer `engines` ranges.
See [`design/PLUGIN-CONTRACT.md`](design/PLUGIN-CONTRACT.md). Roadmap exit
criteria: [`milestones/M-plugins.md`](milestones/M-plugins.md).

**Rules**

1. Plugins are **community / clean-room** only — no MathWorks proprietary
   toolboxes or MATLAB RE.
2. Do not mark plugin-related `feature_map` rows `done` until contract + host
   tests satisfy M-plugins exit criteria.
3. Option comparison (historical): [`design/PLUGIN-OPTIONS.md`](design/PLUGIN-OPTIONS.md).

## Feature status criteria

`docs/feature_map.yaml` statuses are **claims**, not vibes. Use:

| Status | Meaning | Promotion rule |
|--------|---------|----------------|
| `stub` | Protocol, empty body, or explicit `NotImplementedError` only | Default for new seams |
| `partial` | MVP slice demonstrable + automated tests; known gaps listed in `notes` | Default after first landing PR |
| `done` | Every bullet of that feature’s **written acceptance criteria** is true | **Never** flip `partial`→`done` without criteria in an Issue/PR |

### Written criteria (minimum for `done`)

For a given `feature_id`, criteria must name:

1. Observable behaviour (CLI/`-e`/API) or Protocol guarantee
2. Tests that lock it (`tests/…` or Gherkin)
3. Explicit non-goals that do **not** block `done`

Example: `lang.parser` may be `done` for “matrix MVP grammar” while strings remain a different feature_id.

## After-epic sync chore (mandatory)

Before opening the **next** epic’s implementation PRs:

1. Epic acceptance evidence merged (`docs/acceptance/EPIC-NNN.md`)
2. **Chore PR:** `docs/ARCHITECTURE.md` matches tip reality; epic-related `feature_map` **notes** (and statuses only when criteria justify) refreshed
3. Then create/start the next epic board

This chore is project-management, not optional polish.

## Branch protection (manual repo settings)

Recommended for `main` (Settings → Branches → Rule):

1. Require pull request before merging  
2. Require status check: **``test` (Actions job; UI may show as test)`** (job name from Actions)  
3. Require conversation resolution  
4. Do not allow bypass without review (team size permitting)

Documented here because protection is configured in the GitHub UI, not in git.


## Enabling CI on GitHub

The workflow file lives at **`docs/examples/ci.github-actions.yml`** so agents
without the GitHub `workflow` OAuth scope can still push docs. To enable gates:

1. Copy to `.github/workflows/ci.yml` via the GitHub UI (Actions → New workflow)
   or a credential that has the `workflow` scope.
2. Turn on branch protection requiring check **``test` (Actions job; UI may show as test)`**.

## Local commands

```bash
pip install -e ".[dev]"
openmatlab status
openmatlab features
openmatlab cases
pytest -m "unit or bdd" --cov=openmatlab --cov-fail-under=60
openmatlab test --suite unit
```
