# M11 — Debugger and Workbench

GitHub milestone: https://github.com/superche/openmatlab/milestone/11

**Related:**
- [MATLAB-aligned Workbench](M-workbench-aligned.md) (closed, W01–W15): the headless `host/workbench.py` model this milestone extends.
- [M10 Tables and data types](M10-tables.md) runs interleaved; the variable editor (D09) shows tables.
- [`../GAP-ANALYSIS.md`](../GAP-ANALYSIS.md) ("Debugger … variable editor" row).

## Intent

Make OpenMATLAB debuggable the way MATLAB is: `dbstop`/`dbcont`/`dbstep`/`dbstack`/`keyboard`, error stops, full `MException.stack`/`getReport`, surfaced in the Workbench (editor breakpoints, debug toolbar, frame-aware Workspace, variable editor).

Approved by Shaw on 2026-10-16. Decision: the **variable editor (D09) is in scope**.

## Exit criteria (measurable)

M11 is **done** only when **all** of these hold on `main`:

1. **Conformance.** Every criterion in [`tests/conformance/m11_manifest.py`](../../tests/conformance/m11_manifest.py) is `met`, and `pytest tests/conformance/test_m11_conformance.py` reports **0 xfail**.
2. **No open `p0` issue** on milestone/11.
3. **No Python traceback** in a probe sweep over debugger commands and Workbench actions.
4. **Docs.** No doc drift; CI on `main` is green; each epic has an accepted `docs/acceptance/EPIC-NNN.md`; D10 includes one recorded E2E capture (as in M6).

Language criteria (D01–D07) are `.m` scripts over real function files in a `tempname` folder; a sibling `.queue` file holds the lines typed at the `K>>`/`input` prompt. Workbench criteria (D08–D10) are `.py` scripts driving the headless model. All are strict xfail until met.

## Criteria

| # | Criterion | Script | Priority | Epic | Status |
|---|-----------|--------|----------|------|--------|
| D01 | `MException.stack` file/name/line per frame (local functions, class methods), `getReport` basic/extended without hyperlinks, unthrown exception has 0×1 stack; uncaught errors print "Error in f (line N)" | m11_d01_exception_stack_report | p0 | #698 (#565) | met (Epic #698; residual #705) |
| D02 | `dbstack` struct and printed form, `dbstack(n)`, `'-completenames'`, `mfilename` | m11_d02_dbstack | p0 | #698 (#611) | met (Epic #698; residual #705) |
| D03 | `dbstop in f at N` / `in f` / `if expr`, `dbclear` (line, all), `dbstatus`, pause when a breakpoint is hit | m11_d03_breakpoints | p0 | #699 | met (Epic #699; residual #713) |
| D04 | `dbstep`, `dbstep in`, `dbstep out`, `dbcont` with correct lines across loops and local functions; `K>>` prompt; `dbquit` | m11_d04_stepping | p0 | #699 | met (Epic #699; residual #713) |
| D05 | Paused-frame evaluation, `dbup`/`dbdown`, `who`/`exist`/`evalin('caller')` respect the active frame, assignments take effect on resume | m11_d05_paused_workspace | p1 | #699 (#611) | met (Epic #699; residual #713) |
| D06 | `input`, `input(prompt,'s')`, empty input, `keyboard` + `dbcont` | m11_d06_keyboard_input | p1 | #700 (#577) | met (Epic #700; residual #729) |
| D07 | `dbstop if caught error [ID]`, `if error`, `if warning`, `if naninf`; pause at the faulting line with the stack intact | m11_d07_error_stop | p1 | #700 | met (Epic #700; residual #729) |
| D08 | Workbench debug UI: gutter breakpoints ↔ `dbstop`/`dbclear`, current-line marker, Continue/Step/Step In/Step Out/Quit, stack selector rebinding Workspace | m11_d08_workbench_debug_ui | p0 | #701 | met (Epic #701; residual #725) |
| D09 | Variable editor: open numeric/char/cell/struct/table from Workspace, edit a cell and write back | m11_d09_variable_editor | p1 | #702 | met (Epic #702; residual #747) |
| D10 | Workflows: `%%` sections, Run Section, Run and Advance, run with breakpoints, error link → file at line, Command History re-run; recorded E2E capture ([video](../../demos/workbench/showcase_d10_debugger_workflows.mp4)) | m11_d10_workbench_workflows | p1 | #703 | met (Epic #703; residual #751) |

## Epics (approved order, interleaved with M10)

1. **D-E1 #698 (p0):** source positions, `MException.stack`, `getReport`, `dbstack` — D01, D02. **First epic overall.**
2. **D-E2 #699 (p0):** debug engine; pause-model design doc first — D03, D04, D05.
3. **D-E4 #701 (p0):** Workbench debug UI — D08.
4. **D-E3 #700 (p1):** `keyboard`, `input`, condition stops — D06, D07.
5. **D-E5 #702 (p1):** variable editor — D09 (after T-E1).
6. **D-E6 #703 (p1):** Workbench workflows — D10.

Absorbed residuals are referenced, not moved: #565 (`MException.stack`/`getReport`), #611 (`dbstack`, evalin/assignin from nested sessions), #577 (`input`/`keyboard`).

## Non-goals

Profiler, Code Analyzer/LSP, Live Editor, App Designer/`uifigure`, help browser (#611 keeps it), remote or `parfor` debugging, debugging inside Python builtins.

## Risks and design questions

- **Pause model:** recursive tree-walking evaluator; nested REPL vs evaluator thread. Design doc required before D-E2.
- **Overhead:** per-statement hook must cost ~0 with no breakpoints.
- **Line fidelity:** continuation lines, `if`/`end` lines, anonymous functions, classdef methods.

## Progress snapshot

M11 opened 2026-10-16. **10 / 10** criteria met: D01, D02 (Epic #698, [design](../design/EPIC-698-callstack.md)); D03, D04, D05 (Epic #699, [pause-model design](../design/EPIC-699-pause-model.md)); D08 (Epic #701, [design](../design/EPIC-701-debug-ui.md)); D06, D07 (Epic #700, [design](../design/EPIC-700-condition-stops.md)); D09 (Epic #702, [design](../design/EPIC-702-variable-editor.md)); D10 (Epic #703, [design](../design/EPIC-703-workbench-workflows.md)). Next: closed (see Close-out).


## Close-out (2026-10-16)

**Status: closed.** Shaw accepted every epic (#698–#703) on 2026-10-16 (Asia/Shanghai), and the GitHub milestone is closed.

- **Criteria:** 10 / 10 met (D01–D10), with 0 xfails on `main`.
- **Open p0 issues:** none.
- **Doc drift / CI:** D10 recorded E2E at `demos/workbench/showcase_d10_debugger_workflows.mp4` (#759); `main` CI green through tip `70f2933`.
- **Acceptance:** `docs/acceptance/EPIC-698.md` … `EPIC-703.md`.

**Residuals left on closed milestone/11** (p2; not re-homed):

| Issue | Pri | Topic |
|---|---|---|
| #705 | p2 | D-E1 residual (Error using header, nested/anonymous frame names, …) |
| #713 | p2 | D-E2 residual (end-line stops, anonymous breakpoints, …) |
| #725 | p2 | D-E4 residual (Pause button, conditional gutter breakpoints, …) |
| #729 | p2 | D-E3 residual (naninf granularity, input() in Workbench, …) |
| #747 | p2 | D-E5 residual (struct/object editing, insert/delete rows, …) |
| #751 | p2 | D-E6 residual (section-relative error lines, cell-mode highlight, …) |
| #760 | p2 | Workbench fprintf/disp → Command Window (not terminal stdout) |
