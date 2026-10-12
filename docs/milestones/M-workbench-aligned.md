# M-workbench-aligned — MATLAB-aligned Workbench

GitHub milestone: https://github.com/superche/openmatlab/milestone/6

**Related:** Closed Workbench MVP (milestone/1) · Plugin host
[`M-plugins.md`](M-plugins.md) / contract
[`PLUGIN-CONTRACT.md`](../design/PLUGIN-CONTRACT.md) · Minimal desktop
(`openmatlab desktop`, Epic #349 / #368)

## Intent

Ship a **MATLAB Desktop / Workbench–aligned** Host product — not a thin
two-pane notebook. The Host **owns** chrome and layout. Plugins fill **slots**
(panels, menus, commands) — they never fork the shell (PLUGIN-CONTRACT).

### Honest split: panel MVP vs layout parity

| Tier | What | Status |
|------|------|--------|
| **Panel MVP** (W01–W06) | Five host regions with working APIs + tests | **met** |
| **Layout parity** (W07–W15) | Menu bar, toolstrip, classic docks, multi-doc Editor, CW history, Workspace Value, path toolbar, docked Figures, layout presets | **required for milestone exit** — criteria met; epic #372 closed (user accepted) |

Milestone exit is **not** satisfied by panel MVP alone. User acceptance
requires MATLAB-like layout parity (see exit criteria below).

## Exit criteria (measurable)

M-workbench-aligned is **done** only when **all** hold on `main`:

1. **Host shell.** `openmatlab workbench` opens a Host-owned **classic docked**
   layout (Current Folder left · Editor center · Command Window bottom ·
   Workspace + Figures right) with menu bar, toolstrip, and path toolbar.
2. **Panel MVP W01–W06** are `met` with tests (unit and/or BDD).
3. **Layout parity W07–W14** are `met` with tests; **W15** `met` or honestly
   residual with an open Issue. Pending rows use strict honesty (no fake
   `done` in feature_map).
4. **No open `p0` Issue** on this milestone.
5. **Docs sync.** PROCESS / AGENTS / ARCHITECTURE point at this milestone;
   feature_map rows exist for each region; notes list layout-parity gaps.
6. **E2E evidence.** Window recording of the Desktop-like chrome (not the old
   notebook-only UI) attached to Epic #372 acceptance.

## Criteria (priority order — epic selection)

### Panel MVP

| # | Criterion | Priority | Tracking | Status |
|---|-----------|----------|----------|--------|
| W01 | Host Workbench shell + named layout regions / slots | p0 | #377 | **met** |
| W02 | Command Window panel (REPL eval + capture) | p0 | #378 | **met** |
| W03 | Editor panel MVP (open/edit/save `.m`) | p1 | #379 | **met** |
| W04 | Workspace browser (name/size/class + refresh) | p1 | #380 | **met** |
| W05 | Current Folder browser | p1 | #381 | **met** |
| W06 | Figure management panel | p1 | #382 | **met** |

### Layout parity (MATLAB Desktop chrome)

| # | Criterion | Priority | Tracking | Status |
|---|-----------|----------|----------|--------|
| W07 | Menu bar (File / Edit / View / Layout) | p0 | #390 | **met** |
| W08 | Toolstrip / toolbar (Home actions) | p0 | #391 | **met** |
| W09 | Classic docked desktop layout (CF\|Editor/CW\|WS) | p0 | #392 | **met** |
| W10 | Multi-document Editor tabs | p1 | #393 | **met** |
| W11 | Command Window history | p1 | #394 | **met** |
| W12 | Workspace details (Value column) | p1 | #395 | **met** |
| W13 | Current Folder + path toolbar | p1 | #396 | **met** |
| W14 | Docked Figures container | p1 | #397 | **met** |
| W15 | Layout presets (Default / save-restore MVP) | p2 | #398 | **met** |

Epic #372 takes unmet rows in this table (p0 before p1, then table order).

## Required feature_ids

All six feature_ids at least `partial`: `host.workbench.shell`,
`host.workbench.command_window`, `host.workbench.editor`,
`host.workbench.workspace_browser`, `host.workbench.current_folder`,
`host.workbench.figures`. Layout-parity notes must stay honest until W07–W14
met.

## Non-goals

- Browser / micro-frontend workbench (Option D)
- Marketplace
- Closing Epic #349 without user acceptance
- Full IDE (LSP, debugger) as W03/W10 blocker
- Pixel-perfect MathWorks ribbon / proprietary toolbox menus

## Progress snapshot

**Panel MVP:** 6 / 6 met (W01–W06).  
**Layout parity:** 9 / 9 met (W07–W15) — Issues #390–#398 closed by layout-parity PR.  
Epic **#372** closed on GitHub 2026-10-12 11:13 CST (user accepted); milestone closed (milestone/6).
