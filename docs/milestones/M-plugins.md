# M-plugins — VS Code–style plugin host

GitHub milestone: https://github.com/superche/openmatlab/milestone/4

**Contract:** [`docs/design/PLUGIN-CONTRACT.md`](../design/PLUGIN-CONTRACT.md)  
**Prior comparison:** [`docs/design/PLUGIN-OPTIONS.md`](../design/PLUGIN-OPTIONS.md) (merged via #348)

## Intent

Ship a **published** plugin contract and host so **community** domain/UI
plugins can extend OpenMATLAB without forking the shell and **without**
depending on MathWorks proprietary toolboxes.

This milestone is the enablement layer for later “Domain toolboxes”
(community-built). It does not deliver full signal/stats/image libraries.

## Exit criteria (measurable)

M-plugins is **done** only when **all** of the following hold on `main`:

1. **Contract on `main`.** `docs/design/PLUGIN-CONTRACT.md` describes manifest
   `contributes`, slots, activation, Extension Host API, and versioning.
2. **Host package.** `src/openmatlab/extensions/` implements discovery
   (load path + optional entry points), manifest validation, slot registry,
   activation lifecycle, and the v0 Host API modules named in the contract.
3. **CLI inspect.** `openmatlab plugins` (or equivalent QA subcommand) lists
   discovered plugins, versions, activation state, and engine mismatches.
4. **Sample community plugin.** At least one in-repo example under
   `demos/plugins/` (or `examples/plugins/`) follows the **locked** manifest
   (not only the pre-contract option-a/b/c stubs) and registers a command +
   optional path entry.
5. **Tests.** `pytest -m "unit or bdd"` covers: valid/invalid manifests,
   duplicate id warning, activation on command, faulted plugin does not kill
   Session, `engines.openmatlab` reject path.
6. **No open `p0` Issue** on this milestone.
7. **Docs sync.** `PROCESS.md` / `AGENTS.md` point at this milestone; 
   `ARCHITECTURE.md` mentions the extensions seam after the implementing epic.

## Criteria (priority order — epic selection)

| # | Criterion | Priority | Tracking | Status |
|---|-----------|----------|----------|--------|
| P01 | Contract + milestone docs locked on `main` | p0 | #349 (this PR) | **met** |
| P02 | Manifest load/validate + schema tests | p0 | #350 | **met** |
| P03 | Slot registry + contribute/unload by plugin id | p0 | #351 | **met** |
| P04 | Activation predicates + ExtensionContext | p0 | #352 | **met** |
| P05 | Extension Host API v0 (`commands` / `path` / `window` smoke) | p0 | #353 | **met** |
| P06 | Discovery: plugin path + entry points group | p1 | #354 | **met** |
| P07 | CLI `plugins` list + sample community plugin demo | p1 | #355 | **met** |
| P08 | Fault isolation + engines semver range enforcement | p1 | #356 | **met** |

## Non-goals (explicit)

- Porting or wrapping MathWorks proprietary toolboxes
- Micro-frontend / browser Extension Host (Option D)
- Marketplace publishing infrastructure
- Marking domain feature_map rows `done` solely because plugins exist

## Residual / follow-ons

After exit: richer UI slots, out-of-process host, signed plugins — file as
`p2` Issues on this milestone or retarget to Domain toolboxes (milestone/3).

## Progress snapshot

After host + acceptance PRs: **8 / 8** criteria met (P01–P08). Epic **#349** OPEN for user acceptance; children #350–#356 closed. Residuals #359–#362 (p2).
Acceptance: [`docs/acceptance/EPIC-349.md`](../acceptance/EPIC-349.md). Showcase: `demos/plugins/showcase_plugin_host.mp4`.
