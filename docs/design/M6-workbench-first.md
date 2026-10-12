# Design: MATLAB-aligned Workbench first slice (Epic #372)

## Approach

Host-owned `Workbench` with five named regions. W01 registers them; W02
implements Command Window via `ReplSession` + `ConsoleDisplay` capture.
Remaining regions stay `stub` until W03–W06. Plugin panels remain slot
contributions (PLUGIN-CONTRACT) — never fork the shell.

CLI: `openmatlab workbench --list-only` / `--eval CODE` / tk surface.
