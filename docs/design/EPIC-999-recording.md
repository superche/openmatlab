# Epic #999 (V-E6): Workbench recording and the M14 package

Milestone: [M14 C-MAPSS PHM vertical](../milestones/M14-cmapss-vertical.md), criteria V08, V09, V10. Depends on #994–#998. The story script already exists (`demos/cmapss/story_fd001.m`).

## Problem

V01–V07 are a CLI story. V08 is that same script in the Workbench window: Command Window progress and the Figures panel. V09 is the package a third party reruns from tip `main` and the public Zenodo record. V10 is the statement that corpus residuals and milestone/9 do not block that close.

## Design

Same shape as the M13 showcase (`record_m13_graphics_showcase.sh` + `m13_driver.py`):

- `demos/workbench/m14_driver.py` opens the real tk Workbench with cwd `demos/cmapss`. It does not generate or delete `.m` files. xdotool opens `story_fd001.m`, types the docked-figure default into the Command Window, and invokes Run. After the script returns, the driver scrolls the Command Window (size line, then the V03–V07 tail) and clicks the two Figures-panel rows: the lab figure, then the raw / `smoothdata` axes.
- `demos/workbench/record_m14_cmapss_showcase.sh` is the ffmpeg `x11grab` wrapper. `--dry-run` skips ffmpeg and still launches the driver. `--headless` runs no GUI and writes no mp4: `bash -n`, parse the driver, `cmapss fetch`, the story, and `git check-ignore` on the zip, the text, and the export.
- `demos/cmapss/record_story_fd001.sh` execs that wrapper so the story directory has a record entry beside `story_fd001.m`.
- Output file, when a display is captured: `demos/workbench/showcase_m14_cmapss.mp4`. Same commit policy as `showcase_m13_graphics.mp4` (the file is the recording; the C-MAPSS zip and the export PNG/PDF stay gitignored). A copy under `/workspace/recordings/` is made only when that directory is outside the git root, which is how the M13 script behaved when the checkout lived at `/workspace/openmatlab`.

The driver raises the debugger wait from 60s to 180s inside this process only (`debug_ui._TIMEOUT`). The product default is unchanged. A cached story Run is a few seconds; the longer wait is there so a cold export does not trip the Step timeout.

`set(groot,'DefaultFigureWindowStyle','docked')` is typed in the Command Window before Run. The story file does not change, so the CLI conformance scripts still see the same source. The Figures panel only previews docked figures.

## Non-goals

Closing corpus residuals. Opening MIT-BIH. Vendoring CWRU. A second copy of the FD001 numbers. Editing existing tests.

## Adversarial review

| Attack | Result |
|---|---|
| Driver pointed at `demos/cmapss` deletes scripts the way `m13_driver.py` clears its temp project | It does not write or unlink `.m` files |
| `--headless` invents an mp4 | It prints `no mp4 written` and does not start ffmpeg |
| Checkout is `/workspace`, so `/workspace/recordings` is inside the repo | The copy is skipped; only `demos/workbench/showcase_m14_cmapss.mp4` is the artifact |
| Zip or `story_fd001.png` gets committed with the video | Both paths stay gitignored; the headless proof runs `git check-ignore` and `git ls-files` |
| Missed folder click leaves the editor empty and Run does nothing | The next scene opens `story_fd001.m` through the listbox binding |
| `DefaultFigureWindowStyle` did not stick | The driver reads it back and sets `docked` on the session before Run |
