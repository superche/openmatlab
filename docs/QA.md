# Quality Assurance System (Layered)

OpenMATLAB QA is an **explicit five-layer system**. Architecture/docs/stubs stage:
no full language/runtime. Aligns with `host` / `lang` / `runtime` / `numerics` /
`graphics` / `libs` / `qa`.

Clean-room only — no MATLAB binary RE. Optional future conformance sources:
public language docs and public Octave behavior.

```
┌─────────────────────────────────────────────────────────────┐
│ 5. Work / ticket / defect system                              │
│    gaps & bugs → triage → feature_map / test_catalog updates  │
├─────────────────────────────────────────────────────────────┤
│ 4. Test tooling                                               │
│    pytest · openmatlab CLI · qa loaders · (future CI)         │
├─────────────────────────────────────────────────────────────┤
│ 3. Test environments                                          │
│    unit · conformance/golden · interactive · fixtures         │
├─────────────────────────────────────────────────────────────┤
│ 2. Test case / use-case management                            │
│    docs/test_catalog.yaml · use_cases/ · links to tests       │
├─────────────────────────────────────────────────────────────┤
│ 1. Feature management                                         │
│    docs/feature_map.yaml · capability status · depends_on     │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Ownership | Source of truth | CLI / tooling seam |
|-------|-----------|-----------------|--------------------|
| **1. Features** | Product + architecture | `docs/feature_map.yaml` | `openmatlab features` |
| **2. Cases** | QA + domain | `docs/test_catalog.yaml` | `openmatlab cases` |
| **3. Environments** | QA eng | `tests/{unit,conformance,interactive,fixtures}` | `openmatlab test --suite …` |
| **4. Tooling** | Eng | `openmatlab.qa.*`, pytest, pyproject | `openmatlab status\|features\|cases\|test` |
| **5. Work/defects** | All | `docs/defects/` + workflow | `openmatlab defects` (index) |

Human indexes: `docs/FEATURE_MAP.md`, `docs/TEST_CATALOG.md`, `docs/WORKFLOW.md`.

---

## Layer 1 — Feature management

**Purpose:** Inventory *what the product can/should do*, by package layer, with
implementation status — independent of any single test file.

**Artifacts**

| Path | Role |
|------|------|
| `docs/feature_map.yaml` | Machine-readable capability inventory |
| `docs/FEATURE_MAP.md` | Human index + update rules |
| `openmatlab.qa.feature_map` | Load / validate / filter / format |

**Schema (feature row)**

```yaml
- id: layer.capability_snake    # stable
  layer: host|lang|runtime|numerics|graphics|libs|qa
  name: title
  status: planned|stub|partial|done|wontfix
  spec: docs/…                  # optional
  tests: [path…]                # optional links (not source of truth)
  cases: [case.id…]             # optional links into test_catalog
  protocols: [dotted.Name…]
  depends_on: [feature.id…]
  notes: text
```

**Rules**

- Same PR that adds a Protocol/stub updates `feature_map.yaml`.
- Stable `id`s; rename = breaking (prefer new id + `wontfix` old).
- Features describe **capabilities**; test cases (layer 2) describe **checks**.

---

## Layer 2 — Test case / use-case management

**Purpose:** Inventory *what we verify* and *which user journeys matter*, linked
up to features and down to concrete pytest nodes / goldens.

**Artifacts**

| Path | Role |
|------|------|
| `docs/test_catalog.yaml` | Catalog of use cases + test cases |
| `docs/TEST_CATALOG.md` | Human index |
| `docs/use_cases/*.md` | Optional narrative use-case briefs |
| `openmatlab.qa.catalog` | Load / validate / filter |

**Two record kinds in one catalog**

1. **`use_case`** — actor + goal (e.g. “interactive matrix multiply and plot”)
2. **`test_case`** — verifiable check (unit assert, golden, interactive smoke)

```yaml
use_cases:
  - id: uc.interactive_matrix_plot
    title: …
    actor: scientific user
    goal: …
    features: [lang.matrix_literal, graphics.plot_mvp, host.display_policy]
    priority: p0|p1|p2

test_cases:
  - id: tc.workspace_frames
    kind: unit|conformance|interactive
    title: …
    features: [runtime.workspace]
    use_cases: []                  # optional
    impl: tests/unit/test_architecture.py::test_workspace_frames
    status: planned|stub|active|deprecated
    env: unit                      # which environment (layer 3)
```

**Rules**

- Every `active` test_case should have `impl` pointing at a real node when code exists.
- `planned` cases may lack `impl` (backlog).
- Prefer many small `test_case` ids over one mega-case when Array/parser land.

---

## Layer 3 — Test environments

**Purpose:** *Where* and *how* cases run — isolation, markers, fixtures, CI gates.

```
tests/
  unit/                 # fast, no GUI
  conformance/          # golden / public-spec
    golden/             # expected outputs
  interactive/          # plot/REPL smoke
  fixtures/             # shared inputs (.m snippets, JSON arrays later)
  conftest.py           # markers, fixtures
```

| Environment | Marker | Default CI | Notes |
|-------------|--------|------------|-------|
| unit | `unit` | **required** | architecture, map/catalog load, Workspace |
| conformance | `conformance` | required once non-empty | goldens self-authored / public-spec; optional Octave notes |
| interactive | `interactive` | optional / scheduled | may need display; `needs_matplotlib` |

Extra markers: `slow`, `needs_numpy`, `needs_matplotlib`.

**Golden policy:** OpenMATLAB-generated or public-spec expected outputs — never
proprietary MATLAB dumps via RE. Octave cross-check = documented delta, not
silent oracle until tolerances exist.

---

## Layer 4 — Test tooling

**Purpose:** Operators to load inventories, run suites, and (later) CI.

| Tool | Role |
|------|------|
| `pytest` + `[tool.pytest.ini_options]` | Runner + markers |
| `openmatlab status` | Architecture + QA blurb |
| `openmatlab features` | Dump layer-1 map |
| `openmatlab cases` | Dump layer-2 catalog |
| `openmatlab test --suite …` | Subprocess pytest by environment |
| `openmatlab defects` | List defect index (layer 5) |
| `openmatlab.qa.feature_map` / `catalog` / `defects` | Library loaders |
| `openmatlab.qa.paths` | Resolve `docs/*` from editable install |

CLI does **not** reimplement pytest; `test` always delegates.

Reserved: `-e` / script eval → exit 2 until evaluator leaves stub.

---

## Layer 5 — Work / ticket / defect system

**Purpose:** Close the loop: failure or gap → tracked work → feature/case updates.

**Flow**

```
test fail / user gap / review finding
        │
        ▼
docs/defects/DXXXX.md  (or tracker URL noted therein)
        │
        ├─► triage: bug | gap | epic | chore
        ├─► link feature_ids[] + test_case ids[]
        ├─► set severity / status
        ▼
fix code + update feature_map status + activate/add test_cases
        │
        ▼
defect → status: closed (keep file for history)
```

**Artifacts**

| Path | Role |
|------|------|
| `docs/WORKFLOW.md` | Triage rules, states, ownership |
| `docs/defects/README.md` | Index conventions |
| `docs/defects/TEMPLATE.md` | New defect template |
| `docs/defects/D0001.md` … | One file per open/closed item (light, in-repo) |
| `docs/defects/index.yaml` | Machine index for `openmatlab defects` |
| `openmatlab.qa.defects` | Load index |

**States:** `open` → `accepted` → `in_progress` → `resolved` → `closed`  
(or `wontfix` / `duplicate`)

**In-repo vs GitHub Issues:** In-repo YAML/md is the **portable source** for
agents/CI. GitHub Issues remain optional mirrors; if both exist, defect file
holds canonical `feature_ids` / `case_ids` links.

---

## Adversarial scaling (Array / parser land)

| Risk | Mitigation |
|------|------------|
| Features ≠ tests conflated | Layer 1 vs 2 separated; cross-link by id only |
| Catalog bitrots | `openmatlab cases` + unit validate unique ids / known feature refs |
| Goldens = MATLAB RE | Explicit policy in layer 3 |
| CLI becomes second pytest | Layer 4 delegates |
| Defects orphaned from map | Layer 5 requires `feature_ids` on accepted defects |
| Flat tests/ won’t scale | Environments split now |

## Related

- `docs/ARCHITECTURE.md` — product seams  
- Package `openmatlab.qa` — loaders only (no numerics/graphics)
