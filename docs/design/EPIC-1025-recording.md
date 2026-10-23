# Epic #1025 (I-E6): Workbench recording and the M16 package

Milestone: [M16 BBBC038 nuclei image vertical](../milestones/M16-bbbc038-vertical.md), criteria V08, V09, V10. Depends on #1020–#1024. The story script already exists (`demos/bbbc038/story_stage1_test.m`).

## Problem

V01–V07 are a CLI story. V08 is that same script in the Workbench window: Command Window numbers (count, mean area, median, the 300 dpi paths) and the Figures panel. V09 is the package a third party reruns from tip `main` and the public Broad `stage1_test.zip`. V10 is the statement that corpus residuals and milestone/9 do not block that close.

## Design

Same shape as the M15 showcase (`record_m15_mitbih_showcase.sh` + `m15_driver.py`):

- `demos/workbench/m16_driver.py` opens the real tk Workbench with cwd `demos/bbbc038`. It does not generate or delete `.m` files. xdotool opens `story_stage1_test.m`, types the docked-figure default into the Command Window, and invokes Run. After the script returns, the driver shows the V01–V03 head and the V04–V07 tail (count 6, mean area 163), then clicks Figure 1 (raw and mask) and Figure 2 (the area histogram).
- The story closes the 2-by-2 lab figure after the 300 dpi export so the existing V03–V07 checks still see one current 1-by-2 and one histogram. The driver then runs `lab_figure.m` again in that same session and previews Figure 3 (overlay, histogram, summary, CC0 / Caicedo 2019 footnote). The story file is not changed to leave that figure open.
- `demos/workbench/record_m16_bbbc038_showcase.sh` is the ffmpeg `x11grab` wrapper. `--dry-run` skips ffmpeg and still launches the driver. `--headless` runs no GUI and writes no mp4: `bash -n`, parse the driver, the story, and `git check-ignore` on the zip, the FOV PNG, and the export.
- `demos/bbbc038/record_story_stage1_test.sh` execs that wrapper so the story directory has a record entry beside `story_stage1_test.m`.
- Output file, when a display is captured: `demos/workbench/showcase_m16_bbbc038.mp4`. Same commit policy as `showcase_m15_mitbih.mp4` (the file is the recording; the Broad zip, the FOV PNG, and the export PNG/PDF stay gitignored). A copy under `/workspace/recordings/` is made only when that directory is outside the git root.

The driver raises the debugger wait from 60s to 180s inside this process only (`debug_ui._TIMEOUT`). The product default is unchanged. The recorded Run returned in about 3 seconds.

`set(groot,'DefaultFigureWindowStyle','docked')` is typed in the Command Window before Run. The story file does not set that, so the CLI conformance scripts still see the same figure tree. The Figures panel only previews docked figures.

If `.venv` is absent, the wrapper uses `python3`. The M14 script always sources `.venv`; this box had OpenMATLAB on the system interpreter.

## Non-goals

Closing corpus residuals. Reopening C-MAPSS or MIT-BIH. The training zip. Closing epics #1020–#1025 or milestone/16 (Shaw batch-accepts). A new language feature. Editing existing tests.

## Adversarial review

| Attack | Result |
|---|---|
| Driver pointed at `demos/bbbc038` deletes scripts | It does not write or unlink `.m` files |
| Leaving the lab figure open breaks V03–V07 | The story still closes it and calls `figure(1)`. The recording reopens `lab_figure.m` after Run |
| `--headless` invents an mp4 | It prints `no mp4 written` and does not start ffmpeg |
| Checkout is `/workspace`, so `/workspace/recordings` is inside the repo | The copy is skipped; only `demos/workbench/showcase_m16_bbbc038.mp4` is the artifact |
| The zip, the FOV PNG, or `story_stage1_test.png` gets committed with the video | Those paths stay gitignored; the headless proof runs `git check-ignore` and `git ls-files` |
| Missed folder click leaves the editor empty | The next scene opens `story_stage1_test.m` through the listbox binding |
| `DefaultFigureWindowStyle` did not stick | The driver reads it back and sets `docked` on the session before Run |
| `run('lab_figure.m')` typed into the Command Window does not create Figure 3 | The next scene counts figures and, if the count did not grow, evals the absolute path |
| No display on the capture box | The script exits 2 and names `--headless`. This workspace had `DISPLAY=:1` at 1920×1200, so the mp4 is a real grab |
