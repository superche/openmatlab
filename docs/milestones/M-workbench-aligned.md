# M-workbench-aligned — MATLAB-aligned Workbench

GitHub milestone: https://github.com/superche/openmatlab/milestone/6

**Related:** Closed Workbench MVP (milestone/1) · Plugin host
[`M-plugins.md`](M-plugins.md) / contract
[`PLUGIN-CONTRACT.md`](../design/PLUGIN-CONTRACT.md) · Minimal desktop
(`openmatlab desktop`, Epic #349 / #368)

## Intent

Ship a **MATLAB-aligned desktop workbench** as a **Host product**:

- Command Window
- Editor
- Workspace browser
- Current Folder
- Figure management

The Host **owns** chrome and layout. Plugins fill **slots** (panels, menus,
commands) — they never fork the shell (PLUGIN-CONTRACT).

## Exit criteria (measurable)

M-workbench-aligned is **done** only when **all** hold on `main`:

1. **Host shell.** `openmatlab workbench` (or documented equivalent) opens /
   lists a Host-owned layout with the five regions above (stubs allowed only
   where criterion status is still `pending`).
2. **Criteria W01–W06** in the table below are `met` with tests (unit and/or
   BDD); pending rows use strict honesty (no fake `done` in feature_map).
3. **No open `p0` Issue** on this milestone.
4. **Docs sync.** PROCESS / AGENTS / ARCHITECTURE point at this milestone;
   feature_map rows exist for each region.

## Criteria (priority order — epic selection)

| # | Criterion | Priority | Tracking | Status |
|---|-----------|----------|----------|--------|
| W01 | Host Workbench shell + named layout regions / slots | p0 | #377 | **met** |
| W02 | Command Window panel (REPL eval + capture) | p0 | #378 | **met** |
| W03 | Editor panel MVP (open/edit/save `.m`) | p1 | #379 | pending |
| W04 | Workspace browser (name/size/class + refresh) | p1 | #380 | pending |
| W05 | Current Folder browser | p1 | #381 | pending |
| W06 | Figure management panel | p1 | #382 | pending |

Epic #372 takes unmet rows in this table (p0 before p1, then table order).

## Required feature_ids

`host.workbench.shell`, `host.workbench.command_window` at `partial` after
first slice; later `host.workbench.editor`, `host.workbench.workspace_browser`,
`host.workbench.current_folder`, `host.workbench.figures`.

## Non-goals

- Browser / micro-frontend workbench (Option D)
- Marketplace
- Closing Epic #349 without user acceptance
- Full IDE (LSP, debugger) as W03 blocker

## Progress snapshot

After first-slice PR: **2 / 6** criteria met (W01–W02). Epic **#372** OPEN
until acceptance evidence.
