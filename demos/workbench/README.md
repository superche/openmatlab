# Workbench showcase (Epic #372)

MATLAB-aligned Host workbench window recording for milestone/6.

## Artifacts

- [`showcase_workbench.mp4`](showcase_workbench.mp4) — clear-window recording:
  `--list-only` (W01–W06 ready) → headless `--eval` → tk Host walkthrough
  (Editor / Workspace / Current Folder / Figures)
- [`record_showcase.sh`](record_showcase.sh) — ffmpeg + xfce4-terminal helper
- [`showcase_d10_debugger_workflows.mp4`](showcase_d10_debugger_workflows.mp4) — M11 D10 E2E capture
  (Epic #703): breakpoints, stepping, Variables editor, stack selector, Run Section /
  Run and Advance, error hyperlink. Re-record: `DISPLAY=:2 ./demos/workbench/record_d10_showcase.sh`
  (driver: [`d10_driver.py`](d10_driver.py))
- [`sample_project/`](sample_project/) — cwd used by Current Folder / Editor demo
- [`showcase_m14_cmapss.mp4`](showcase_m14_cmapss.mp4) — M14 V08 capture of
  `demos/cmapss/story_fd001.m` (Command Window + Figures). Re-record:
  `DISPLAY=:2 ./demos/workbench/record_m14_cmapss_showcase.sh`
  (driver: [`m14_driver.py`](m14_driver.py)). No display:
  `./demos/workbench/record_m14_cmapss_showcase.sh --headless` (no mp4).

## Re-record

```bash
DISPLAY=:2 ./demos/workbench/record_showcase.sh
```
