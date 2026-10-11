# Quality Assurance System (Layered, off-the-shelf preferred)

**R&D iteration loop + Definition of Done:** [`PROCESS.md`](PROCESS.md) · [`../CONTRIBUTING.md`](../CONTRIBUTING.md)

Behaviour specs: `features/*.feature` (pytest-bdd). CI: `.github/workflows/ci.yml`.

OpenMATLAB QA is a **five-layer** system. Prefer **existing tools** (GitHub
Issues, `gh`, pytest, coverage; later Selenium/Playwright for web UI) over
bespoke trackers. Architecture/docs stage — no full language/runtime.

Packages: `host` / `lang` / `runtime` / `numerics` / `graphics` / `libs` / `qa`.

Clean-room — no MATLAB binary RE. Optional conformance: public docs / Octave.

```
┌─────────────────────────────────────────────────────────────┐
│ 5. Work / defects     → GitHub Issues + gh (+ issue templates)│
├─────────────────────────────────────────────────────────────┤
│ 4. Test tooling       → pytest, coverage, gh, openmatlab CLI │
├─────────────────────────────────────────────────────────────┤
│ 3. Test environments  → unit / conformance / interactive     │
├─────────────────────────────────────────────────────────────┤
│ 2. Test / use cases   → pytest nodes + docs/test_catalog.yaml│
├─────────────────────────────────────────────────────────────┤
│ 1. Features           → docs/feature_map.yaml (inventory)    │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Canonical system | Custom (kept thin) | Why custom at all |
|-------|------------------|--------------------|-------------------|
| **1 Features** | **GitHub Issues** (+ optional **Projects**) | `docs/feature_map.yaml` sync/export | Issues track work; YAML is optional inventory sync |
| **2 Cases** | **pytest** + **pytest-bdd** / Gherkin | `features/*.feature`, `docs/test_catalog.yaml` | Behaviour in Gherkin; catalog links impl nodes |
| **3 Envs** | pytest markers + dirs | layout under `tests/` | Standard layout; not a new framework |
| **4 Tooling** | **pytest**, **coverage**, **gh** | `openmatlab` CLI wrappers | Thin DX only |
| **5 Defects** | **GitHub Issues** | templates + label conventions | **No** in-repo defect ledger |

---

## Layer 1 — Feature management

**Canonical work items:** GitHub Issues (+ optional Projects board).  
**Sync/export:** `docs/feature_map.yaml` · index `docs/FEATURE_MAP.md`  
**CLI:** `openmatlab features` · labels documented in `PROCESS.md`

Status values in YAML: `planned|stub|partial|done|wontfix`. Update YAML in the
same PR when capability status changes — it is **not** a second ticket DB.

---

## Layer 2 — Test case / use-case management

**Behaviour specs:** Gherkin in `features/*.feature` via **pytest-bdd**.  
**Canonical execution:** pytest (`tests/unit`, `tests/bdd`).  
**Catalog:** `docs/test_catalog.yaml` links features ↔ impl nodes.  
**CLI:** `openmatlab cases`  
Issues track *work*; Gherkin+catalog track *verification*.

---

## Layer 3 — Test environments

```
tests/unit/            # pytest -m unit        (CLI/REPL/logic — default gate)
tests/conformance/     # pytest -m conformance (golden / public-spec)
tests/interactive/     # pytest -m interactive (smoke; optional in CI)
tests/fixtures/
```

| Environment | Tooling preference |
|-------------|-------------------|
| unit | **pytest** (in-process) |
| conformance | **pytest** + golden files under `conformance/golden/` |
| CLI smoke | **pytest** + `subprocess` (not Selenium) |
| interactive REPL | pytest subprocess / pexpect-style later — still not browser |
| **Future web workbench UI** | **Playwright or Selenium** — only when a browser UI exists |

**Today’s product is CLI/REPL** — do **not** add Selenium/Playwright until there
is a web UI. Goldens are self-authored / public-spec; never proprietary MATLAB RE.

---

## Layer 4 — Test tooling

| Tool | Use |
|------|-----|
| **pytest** + **pytest-bdd** | Unit + Gherkin scenarios |
| **coverage** (`pytest-cov`) | CI `--cov-fail-under=60` (modest) |
| **GitHub Actions** | PR/main CI (`.github/workflows/ci.yml`) |
| **gh** | Issues / PRs (layer 5) |
| **openmatlab** CLI | `status` · `features` · `cases` · `defects` (→ gh) · `test` (→ pytest) |
| Playwright / Selenium | Deferred — future web workbench only |

```bash
pip install -e ".[dev]"
openmatlab test --suite unit
pytest -m unit --cov=openmatlab --cov-report=term-missing   # when pytest-cov installed
```

`openmatlab test` **subprocess**-es pytest; it does not reimplement a runner.

---

## Layer 5 — Work / defects (GitHub Issues)

**Canonical:** GitHub Issues.  
**CLI:** `gh issue …` or `openmatlab defects` (lists via `gh` if available).  
**Bridge only:** `.github/ISSUE_TEMPLATE/` (bug/gap) with `feature_ids` / `case_ids`
fields; labels `layer:*`, `bug|gap|epic|chore`.  
**Removed as source of truth:** in-repo `D####.md` / `defects/index.yaml` ledgers.

See `docs/WORKFLOW.md` and `docs/defects/README.md` (pointer page only).

```
pytest fail / gap / review
       → gh issue create (template)
       → link feature_ids + case_ids
       → PR updates feature_map + catalog
       → close issue
```

---

## Adversarial notes

| Risk | Mitigation |
|------|------------|
| Second ticket DB drifts from GitHub | Issues canonical; docs/defects is pointer only |
| Selenium forced too early | Explicitly deferred until web UI |
| Catalog vs Issues confusion | Cases = verification inventory; Issues = work items |
| Feature YAML vs Projects | YAML stays inventory; Projects optional later |

## Related

`docs/ARCHITECTURE.md` · `docs/FEATURE_MAP.md` · `docs/TEST_CATALOG.md` · `docs/WORKFLOW.md`
