# Plugin architecture options (domains + Desktop/UI)

**Status:** comparison only — **do not** treat this as the locked plugin
contract or milestone. After a pick, write contract + milestone separately.

**Goal:** Domain libraries as plugins **and** Desktop/UI as plugins (full
shell **or** panels). Domains may customize UX without forking the host.

**Demos:** `demos/plugins/option-{a,b,c,d}/` (stdlib-first stubs; run
`python demos/plugins/option-N/run_demo.py`).

Related seams today: `ToolboxPath`, `FunctionResolver`, `Session`,
`PlotSurface` / `GraphicsBackend`, `host/` CLI+REPL (`docs/ARCHITECTURE.md`).
Roadmap context: Milestone **Domain toolboxes** (GitHub milestone/3).

---

## Shared requirements (all options must address)

| Need | Notes |
|------|--------|
| Domain plugins | Register commands / `.m` path / builtins / numerics helpers |
| UI plugins | Contribute panels **or** replace/compose shell chrome |
| Domain → UX | Domain can nudge layout, default panels, menus, themes |
| Discovery | How host finds plugins (packaging, path, hard-wire) |
| Isolation | Fail one plugin without killing Session |
| KISS / LSP | Fit AGENTS.md; Protocols at seams; no RE of MATLAB |

---

## Option A — Entry-point / `importlib.metadata` discovery

**Idea:** Plugins are installable Python distributions. They advertise
groups such as `openmatlab.domain` and `openmatlab.ui` via packaging
entry points. Host calls `importlib.metadata.entry_points(group=…)` and
`load()`s factories. Domains optionally call a UX hook on the shell.

**Demo:** `demos/plugins/option-a/` (in-process entry table stubs the
same shape as real entry points).

| Pros | Cons |
|------|------|
| Standard Python packaging; pip / wheels / version pins | Awkward for “drop a folder on path” MATLAB-style workflows |
| Clear ownership / dependency resolution | Local/dev toolboxes need editable installs or fake entry tables |
| Good for third-party ecosystem later | Entry-point groups alone do not define **what** may be contributed |
| | UI customization still needs a host API (slots) underneath |

**When to use:** Primary distribution story for **published** plugins;
secondary discovery layer on top of a slot contract.

---

## Option B — Manifest YAML + load path (ToolboxPath-like)

**Idea:** Ordered load path of toolbox folders (extends mental model of
`addpath` / `ToolboxPath`). Each folder has `plugin.yaml` listing
`provides:` symbols (`pkg.mod:attr`). Host imports and invokes them for
commands, panels, and UX hooks.

**Demo:** `demos/plugins/option-b/` (`signal_tb`, `control_tb`).

| Pros | Cons |
|------|------|
| Matches MATLAB toolbox / path UX; low ceremony for authors | YAML + import coupling; versioning weaker than packaging |
| Works for unpackaged / in-repo / user folders | Need careful `sys.path` / collision rules |
| Reuses existing `libs/path.py` instincts | Manifest can drift from code; validation required |
| Domains can declare UI+UX in same folder | Does not by itself prevent host/UI API sprawl |

**When to use:** First-class **authoring & discovery** for domain
toolboxes and in-tree plugins; pair with stable contribution APIs.

---

## Option C — Host extension points (slots) + thin adapters

**Idea:** Host **owns** named slots (`commands`, `panels`, `menus`,
`toolbar`, `status`, `ux_hints`, …). Plugins are thin **adapters** that
only fill slots. Domains customize UX by contributing to the same slots
(hints, default panels, menu paths) — they never fork the shell.
Discovery is orthogonal (wire A, B, or both later).

**Demo:** `demos/plugins/option-c/` (`SignalAdapter`, `CoreShellAdapter`).

| Pros | Cons |
|------|------|
| Clear contract surface; LSP-friendly Protocols | Must design slots carefully up front (evolve with care) |
| Domains customize UX without owning Desktop | “Full shell replacement” is just another adapter — still constrained |
| Discovery-agnostic (A and/or B plug in) | More host code than pure path-of-`.m` |
| Aligns with existing Protocol seams (`Session`, backends) | Over-slotting = premature abstraction (resist) |

**When to use:** **Recommended core architecture** whenever Desktop/UI
is pluginized and domains must customize UX safely.

---

## Option D — Micro-frontend-ish UI plugins (optional)

**Idea:** Each UI plugin is an isolated **bundle** with its own mount
function; shell composes mounts; cross-talk via a message bus. Domains
ship domain API + optional UI bundle; layout prefs are messages, not
shared widget imports.

**Demo:** `demos/plugins/option-d/`.

| Pros | Cons |
|------|------|
| Strong UI isolation; team-scale UI ownership | Heavy for current Python CLI/REPL + Matplotlib MVP |
| Natural fit for a future **web** workbench | Bus/protocol design cost; harder debugging |
| Domains customize UX via events | Weak fit for single-process desktop today (KISS) |

**When to use:** Revisit if/when OpenMATLAB adds a browser workbench
(see PROCESS note on future web UI). Not the first Desktop strategy.

---

## Comparison table

| Criterion | A Entry points | B Manifest+path | C Host slots | D Micro-frontend |
|-----------|----------------|-----------------|--------------|------------------|
| Domain plugins | Strong (packaged) | Strong (folders) | Strong (adapters) | Medium (via bundles) |
| UI panels / shell | Needs host API | Needs host API | **Native** | Strong (isolated) |
| Domain customizes UX | Hook on shell | `provides.ux` | **Same slots** | Bus messages |
| Fits ToolboxPath / MATLAB users | Weak | **Strong** | Neutral | Weak |
| Python packaging ecosystem | **Strong** | Medium | Neutral | Weak today |
| KISS for v0 Desktop | Medium | Strong | **Strong** | Weak |
| Isolation / crash containment | Process=one | Process=one | Process=one | Better UI isolation |
| Aligns with Protocol seams | Medium | Medium | **Strong** | Medium |
| Demo path | `option-a/` | `option-b/` | `option-c/` | `option-d/` |

---

## Recommendation (not locked)

**Recommend Option C as the architecture backbone**, with **Option B as
the default discovery/authoring path** for domain toolboxes, and
**Option A as an optional packaging/distribution layer** for published
plugins.

### Why

1. **Slots are the real contract.** Entry points and YAML only answer
   *how to find* plugins; they do not define safe contribution shapes.
   Domains customizing UX without forking Desktop is exactly “fill the
   same slots.”
2. **B matches the product.** Milestone “Domain toolboxes” and existing
   `ToolboxPath` make folder+manifest the path of least surprise for
   MATLAB-shaped authors.
3. **A is complementary, not competing.** Third-party wheels can expose
   the same adapters via entry points that ultimately call `attach(host)`.
4. **D is premature.** Keep as a future option if a web shell appears;
   do not pay micro-frontend cost for the local workbench first.

### Suggested shape (after user picks — still not a contract)

```
Host (slots: commands, panels, menus, toolbar, status, ux_hints, …)
  ▲ thin adapters (domain.* / ui.*)
  │
  ├── discovery B: load path + plugin.yaml  (default for toolboxes)
  └── discovery A: importlib.metadata      (optional for pip plugins)
```

Full shell plugin = adapter that fills chrome slots (`menus` / `toolbar`
/ `status`); panel plugin = contributes to `panels` only; domain plugin
= `commands` (+ optional UX contributions).

### Explicit non-recommendation for “first lock”

- **A alone** — discovery without contribution API.
- **B alone** — same gap; risk of ad-hoc host hooks.
- **D first** — over-architecture vs current host.

---

## Next steps (blocked on user pick)

1. User chooses: **C+B (+A later)** as recommended, or another row.
2. Then (separate PR): lock **plugin contract** (slot Protocols, YAML
   schema, error isolation) + **milestone** criteria.
3. Do **not** mark feature_map plugin items `done` until contract lands.

---

## How to run demos

```bash
cd /workspace/openmatlab
. .venv/bin/activate   # optional
python demos/plugins/option-a/run_demo.py
python demos/plugins/option-b/run_demo.py
python demos/plugins/option-c/run_demo.py
python demos/plugins/option-d/run_demo.py
```

All four print `OK` on success.
