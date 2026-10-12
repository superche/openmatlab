# Plugin contract (VS Code–style host)

**Status:** **locked** (user pick 2026-10-11). Supersedes the open
recommendation in [`PLUGIN-OPTIONS.md`](PLUGIN-OPTIONS.md). Options A–D demos
remain illustrative; implement against **this** contract.

**Decision:** VS Code–style **plugin host** — published contribution contract +
**community** plugins. Architecture backbone = **Option C (host slots)**;
default discovery/authoring = **Option B (manifest + load path)**; optional
distribution = **Option A (`importlib.metadata` entry points)**. Option D
(micro-frontends) stays deferred.

**Out of scope / non-goals**

- MathWorks proprietary toolboxes, MATLAB App Designer packs, or any reverse
  engineering of MATLAB binaries / internals (clean-room / public specs only;
  see `AGENTS.md`).
- A second work-tracking system — delivery is GitHub Issues + milestone
  [`M-plugins`](../milestones/M-plugins.md).
- Marking `feature_map` plugin rows `done` before host + contract tests land.

---

## Mental model (VS Code → OpenMATLAB)

| VS Code | OpenMATLAB |
|---------|------------|
| `package.json` `contributes` | Manifest `contributes` (`plugin.yaml` or `openmatlab.plugin.json`) |
| Contribution points | **Slots** owned by the host |
| `activationEvents` | `activation` in the manifest |
| `vscode` Extension API | **Extension Host API** (`openmatlab.extensions` surface) |
| Extension Host process | Same-process host for v0 (isolation = try/except + unload); out-of-process later if needed |
| Marketplace / VSIX | Community folders on load path + optional pip wheels (entry points) |

Plugins **never** fork the Desktop shell. They fill slots and call the Host API.

---

## Manifest

Each plugin root is a directory (toolbox-style) containing a manifest file.

**Preferred name:** `plugin.yaml` (MATLAB-path friendly).  
**Also accepted:** `openmatlab.plugin.json` (same schema, JSON).

### Top-level fields

| Field | Required | Meaning |
|-------|----------|---------|
| `id` | yes | Stable plugin id (`publisher.name` or single token, e.g. `community.signal`) |
| `version` | yes | SemVer string (`1.0.0`) |
| `displayName` | no | Human label |
| `description` | no | Short summary |
| `engines.openmatlab` | yes | Host API range this plugin targets (see [Versioning](#versioning--compatibility)) |
| `main` | yes* | Python module path relative to plugin root, or dotted import once on `sys.path` (entry that exports `activate` / `deactivate`) |
| `activation` | no | List of activation predicates (default: `onStartupFinished` if omitted → activate after host ready) |
| `contributes` | no | Declarative contributions (registered **before** `activate` runs) |
| `enabledApiProposals` | no | Reserved; empty for v0 |

\*Packaging-only plugins that only contribute path/data may omit `main` if
`contributes` is purely declarative and needs no runtime module (rare).

### Example (`plugin.yaml`)

```yaml
id: community.signal
version: 0.1.0
displayName: Community Signal Helpers
description: Example domain plugin (not a MathWorks toolbox)
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - onCommand:community.signal.demo
  - onStartupFinished
contributes:
  commands:
    - command: community.signal.demo
      title: "Signal: Demo"
  menus:
    - path: Tools/Signal
      command: community.signal.demo
  panels:
    - id: community.signal.panel
      title: Signal
      when: workspaceHasMatlabFiles
  pathEntries:
    - relative: mfiles
  builtins:
    - name: fir1
      factory: extension:register_fir1
  uxHints:
    defaultPanels:
      - community.signal.panel
```

### `contributes` keys (v0)

Host **owns** these contribution points. Unknown keys → load warning, not crash.

| Key | Payload shape (summary) | Slot filled |
|-----|-------------------------|-------------|
| `commands` | `{ command, title, category? }[]` | `commands` (metadata); handler bound in `activate` or via `builtins`/`main` |
| `menus` | `{ path, command, when? }[]` | `menus` |
| `toolbar` | `{ id, command, title? }[]` | `toolbar` |
| `panels` | `{ id, title, when? }[]` | `panels` |
| `status` | `{ id, text?, command? }[]` | `status` |
| `pathEntries` | `{ relative }` or absolute path strings | extends `ToolboxPath` |
| `builtins` | `{ name, factory }` — `factory` is `module:attr` resolving to a callable factory | `commands` / resolver builtins |
| `uxHints` | `{ defaultPanels?, preferredLayout?, themes? }` | `ux_hints` |
| `configuration` | JSON-schema-ish settings contributions | `configuration` (v0: store only) |

Declarative entries are applied by the host **before** calling `activate`, so
commands/menus appear even if activation is deferred (handlers may be stubs
until activate).

---

## Slots (host extension points)

The host defines named slots. Plugins only **contribute**; they do not replace
the slot registry.

### Core slots (v0 — must exist)

| Slot | Description |
|------|-------------|
| `commands` | Command id → callable (+ metadata from manifest) |
| `panels` | Dockable / tab panel descriptors |
| `menus` | Menu path contributions |
| `toolbar` | Toolbar actions |
| `status` | Status-bar items |
| `ux_hints` | Domain-driven UX preferences (default panels, layout hints) |
| `configuration` | Setting contributions |
| `path` | Extra `.m` search path entries (bridges `ToolboxPath`) |

### Rules

1. **Host owns schemas.** Adding a slot is a Host API change (semver).
2. **LSP.** Slot payloads are Protocols / TypedDicts; adapters must not break
   callers (AGENTS.md).
3. **No shell fork.** “Full Desktop chrome” = contributing to `menus` /
   `toolbar` / `status` / `panels`, not replacing `Host`.
4. **KISS.** Do not add slots until a real plugin needs them (Occam / Deslop).

Reference stub shape: `demos/plugins/option-c/host.py`.

---

## Activation

### Lifecycle

```
discover → validate manifest → register contributes (declarative)
    → wait for activation predicate
    → import main → activate(context) → (optional) deactivate()
```

### Activation predicates (v0)

| Predicate | Fires when |
|-----------|------------|
| `onStartupFinished` | Host finished initial wiring (Session, path, UI shell if any) |
| `onCommand:<commandId>` | That command is first invoked |
| `onPathExists:<glob>` | A file matching glob appears on ToolboxPath / cwd (best-effort) |
| `workspaceHasMatlabFiles` | Activation **or** `when`: any `*.m` on path / workspace roots |

Unknown predicates → warning; plugin stays inactive until a known one fires.

**Path/workspace activation (v0):** `PluginHost.poll_path_activation()` scans
cwd + ToolboxPath (best-effort; also runs at the end of `activate_on_startup`).
It is a poll/hook, not a full filesystem watcher. Call it again after
`addpath` or workspace changes when those predicates matter.

### `ExtensionContext` (passed to `activate`)

| Member | Role |
|--------|------|
| `plugin_id` | Manifest `id` |
| `extension_path` | Absolute plugin root |
| `subscriptions` | List; host calls `.dispose()` on unload |
| `workspace` | Read-only view: cwd, path snapshot |
| `host` | Bound **Extension Host API** (below) |

`activate(context) -> None`. Exceptions are caught, logged, plugin marked
**faulted**; other plugins continue.

`deactivate()` optional; best-effort on unload / shutdown.

---

## Extension Host API

Stable import surface for plugin authors (analogous to `vscode`):

```python
# In plugin main — host injects / plugins import the published package:
from openmatlab.extensions import commands, window, workspace, path as om_path
```

### v0 modules (normative intents)

| API | Capability |
|-----|------------|
| `commands.register_command(id, callback)` | Bind handler; id should match a contributed command |
| `commands.execute_command(id, *args)` | Invoke another command |
| `window.show_information_message(msg)` | Host-appropriate UI or REPL print |
| `window.register_panel(id, factory)` | Attach panel widget/factory to `panels` slot |
| `workspace.get_configuration(section)` | Read contributed settings |
| `om_path.addpath(entry)` / `om_path.which(name)` | Thin wrappers over `ToolboxPath` |
| `extensions.get_extension(id)` | Inspect another plugin’s metadata / public exports; missing id → `KeyError`; faulted plugins returned flagged (`is_active=False`, `error` set) |

Implementation lives under `src/openmatlab/extensions/` (new package). Plugins
must not import private `openmatlab.runtime._*` or poke `Session` internals
except through documented Protocols.

### Isolation

- One plugin’s exception must not tear down `Session`.
- Unload removes that plugin’s slot contributions tagged with its `plugin_id`.
- Same-process v0: no security sandbox; trust community code like any
  `pip install` (document clearly). Future: optional subprocess host.

---

## Discovery

Ordered, first wins on id collision (warn on duplicate `id`):

1. **Built-in / in-repo** plugins shipped with OpenMATLAB (if any).
2. **Load path** — directories from config / env
   `OPENMATLAB_PLUGIN_PATH` (pathsep-separated) + user plugin dir
   (`~/.openmatlab/plugins` or platform equivalent).
3. **Entry points** — group `openmatlab.plugins` → loads distribution that
   exposes a plugin root or factory returning an adapter (Option A). Each
   entry must still resolve to a validated manifest + `activate`.

Discovery answers *where*; slots + Host API answer *what*.

---

## Versioning & compatibility

### Host API version

- Host publishes **`openmatlab.extensions.api_version`** as SemVer
  (independent of package `openmatlab` version if needed; may start aligned).
- Manifest `engines.openmatlab` uses npm-style ranges subset:
  `>=X.Y.Z`, `<X.Y.Z`, exact `X.Y.Z`, and combinations with space = AND.
- Incompatible range → **do not activate**; surface a clear error in
  `openmatlab plugins` / startup log.

### Compatibility policy

| Change | SemVer bump |
|--------|-------------|
| New optional slot / API additive | MINOR |
| New required manifest field / remove slot / change payload meaning | MAJOR |
| Bugfix, docs | PATCH |

Plugins SHOULD declare the narrowest range they test against.

### Compatibility tests (milestone exit)

- Golden manifests (valid / invalid) under `tests/unit/extensions/`.
- Load a sample community plugin from `demos/plugins/` (contract-aligned
  successor to option-b/c stubs) without crashing host when the plugin raises
  in `activate`.

---

## Authoring checklist (community plugin)

1. Create folder with `plugin.yaml` + `main` module.
2. Declare `engines.openmatlab` and `contributes`.
3. Implement `activate(context)`; register command handlers.
4. Put `.m` helpers under a contributed `pathEntries` folder if needed.
5. Optional **`contributes.builtins`**: each entry is `{ name, factory }` where
   `factory` is `module:attr` relative to the plugin root (e.g.
   `extension:make_fir1`). The resolved attr must be a **zero-arg factory** that
   returns a `CallableFunction` (`fn(args, *, nargout=1) -> Sequence[Value]`).
   The host calls the factory at load time and registers the result on
   `FunctionResolver.builtins` (requires a Session / resolver bound to the host).
6. Do **not** vendor proprietary MathWorks code; clean-room / public domain /
   your own MIT/Apache/etc. only.
7. Test against the Host API version you declare.

---


## `when` expression subset (v0)

Menu and panel contributions may carry an optional `when` string. The host
evaluates a **documented subset** (no general expression language yet):

| Expression | Meaning |
|------------|---------|
| omitted / empty / `true` | Always contribute / show |
| `false` | Never contribute / show |
| `workspaceHasMatlabFiles` | Any `*.m` under cwd or ToolboxPath roots |

Unknown identifiers → load/list **warning**, treat as **false**. Boolean
combinations (`&&` / `||` / `!`) are **deferred**.

Host helpers: `PluginHost.list_menus()` / `list_panel_contributions()` apply
this filter. The minimal desktop chrome (`openmatlab desktop`) already renders
real panel widgets via `window.register_panel` (see #368); `when` gates which
declarative panel/menu rows are considered active.

---

## Mapping from PLUGIN-OPTIONS

| Option | Role under this contract |
|--------|--------------------------|
| **C** Host slots | **Normative** extension surface |
| **B** Manifest + path | **Default** discovery + authoring |
| **A** Entry points | **Optional** packaging/distribution |
| **D** Micro-frontend | Deferred (web workbench only) |

---

## Implementation package sketch (non-binding layout)

```
src/openmatlab/extensions/
  __init__.py          # api_version, public re-exports
  manifest.py          # load/validate plugin.yaml | json
  slots.py             # Slot registry
  activation.py        # predicates + lifecycle
  when.py              # menu/panel when subset
  context.py           # ExtensionContext
  discovery.py         # path + entry_points
  api/
    commands.py
    window.py
    workspace.py
    path.py
    extensions.py      # get_extension(id)
```

Exact module split may vary; public names above are the contract.

---

## Related

- Comparison (historical): [`PLUGIN-OPTIONS.md`](PLUGIN-OPTIONS.md)
- Milestone + exit criteria: [`../milestones/M-plugins.md`](../milestones/M-plugins.md)
- Process: [`../PROCESS.md`](../PROCESS.md) § Milestones
- Demos: `demos/plugins/option-{a,b,c,d}/`
