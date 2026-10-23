# Epic #1013 (B-E6): Workbench recording and the M15 package

Milestone: [M15 MIT-BIH Arrhythmia vertical](../milestones/M15-mitbih-vertical.md), criteria V08, V09, V10. Depends on #1008–#1012. The story script already exists (`demos/mitbih/story_record100.m`).

## Problem

V01–V07 are a CLI story. V08 is that same script in the Workbench window: Command Window progress (Fs, peak count, mean RR) and the Figures panel. V09 is the package a third party reruns from tip `main` and public PhysioNet record 100. V10 is the statement that corpus residuals and milestone/9 do not block that close.

## Design

Same shape as the M14 showcase (`record_m14_cmapss_showcase.sh` + `m14_driver.py`):

- `demos/workbench/m15_driver.py` opens the real tk Workbench with cwd `demos/mitbih`. It does not generate or delete `.m` files. xdotool opens `story_record100.m`, types the docked-figure default into the Command Window, and invokes Run. After the script returns, the driver shows the Fs line and the V04–V07 tail, then clicks Figure 4 (the 2×2 lab figure) and Figure 5 (raw and filtered, the last figure).
- `demos/workbench/record_m15_mitbih_showcase.sh` is the ffmpeg `x11grab` wrapper. `--dry-run` skips ffmpeg and still launches the driver. `--headless` runs no GUI and writes no mp4: `bash -n`, parse the driver, `mitbih fetch`, the story, and `git check-ignore` on `100.hea` / `100.dat` / `100.atr` and the export.
- `demos/mitbih/record_story_record100.sh` execs that wrapper so the story directory has a record entry beside `story_record100.m`.
- Output file, when a display is captured: `demos/workbench/showcase_m15_mitbih.mp4`. Same commit policy as `showcase_m14_cmapss.mp4` (the file is the recording; the PhysioNet bytes and the export PNG/PDF stay gitignored). A copy under `/workspace/recordings/` is made only when that directory is outside the git root.

The driver raises the debugger wait from 60s to 180s inside this process only (`debug_ui._TIMEOUT`). The product default is unchanged. The recorded Run returned in about 8 seconds.

`set(groot,'DefaultFigureWindowStyle','docked')` is typed in the Command Window before Run. The story file does not change, so the CLI conformance scripts still see the same source. The Figures panel only previews docked figures.

If `.venv` is absent, the wrapper uses `python3`. The M14 script always sources `.venv`; this box had OpenMATLAB on the system interpreter.

## Non-goals

Closing corpus residuals. Reopening C-MAPSS. Any MIT-BIH record other than 100. Closing epics #1008–#1013 or milestone/15 (Shaw batch-accepts). A new language feature. Editing existing tests.

## Adversarial review

| Attack | Result |
|---|---|
| Driver pointed at `demos/mitbih` deletes scripts | It does not write or unlink `.m` files |
| `--headless` invents an mp4 | It prints `no mp4 written` and does not start ffmpeg |
| Checkout is `/workspace`, so `/workspace/recordings` is inside the repo | The copy is skipped; only `demos/workbench/showcase_m15_mitbih.mp4` is the artifact |
| `100.dat` or `story_record100.png` gets committed with the video | Both paths stay gitignored; the headless proof runs `git check-ignore` and `git ls-files` |
| Missed folder click leaves the editor empty | The next scene opens `story_record100.m` through the listbox binding |
| `DefaultFigureWindowStyle` did not stick | The driver reads it back and sets `docked` on the session before Run |
| No display on the capture box | The script exits 2 and names `--headless`. This workspace had `DISPLAY=:1` at 1920×1200, so the mp4 is a real grab |
