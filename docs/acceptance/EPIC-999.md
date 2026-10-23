# Acceptance evidence: Epic #999 (V-E6 Workbench recording and package)

**Epic:** [#999](https://github.com/superche/openmatlab/issues/999)  
**Milestone:** [C-MAPSS PHM vertical (M14)](https://github.com/superche/openmatlab/milestone/14) · [`docs/milestones/M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md)  
**Design:** [`docs/design/EPIC-999-recording.md`](../design/EPIC-999-recording.md)  
**Batch package:** [`M14-cmapss-vertical.md`](M14-cmapss-vertical.md)  
**Captured:** 2026-10-23  
**Functional tip:** `e21cb43a46c033b0ccf37e99df70851a97ccc619` (the commit that adds the recording; re-run on that commit or a descendant)  
**Rule:** Outputs below come from real local commands. None are invented. The mp4 is an ffmpeg `x11grab` of the live tk Workbench. It is not a stand-in.

## Verdict

**Accepted.** Shaw accepted Epic #999 on 2026-10-23 (Asia/Shanghai); M14 criteria V08, V09, and V10 are **met**. Milestone/14 is closed (**10 / 10**, V01–V10).

The Workbench window opens `demos/cmapss/story_fd001.m`, runs it, prints the FD001 size and the V03–V07 lines in the Command Window, and shows both docked figures in the Figures panel (lab figure, then the raw / `smoothdata` axes). The recording is [`demos/workbench/showcase_m14_cmapss.mp4`](../../demos/workbench/showcase_m14_cmapss.mp4) (120.5 s, 1920×1200). Re-record on the usual box with `DISPLAY=:2 ./demos/workbench/record_m14_cmapss_showcase.sh`.

A third party reproduces the story from tip `main` and the public Zenodo record. The zip, the FD001 text, and the exported PNG/PDF are not in the repo. Corpus residuals and milestone/9 do not block close. No `m14-blocker` issue exists.

## Licence and citation

NASA C-MAPSS, record [15346912](https://zenodo.org/records/15346912), DOI [10.5281/zenodo.15346912](https://doi.org/10.5281/zenodo.15346912), licence CC BY 4.0.

Citation: A. Saxena, K. Goebel, D. Simon, and N. Eklund, "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08, 2008.

The zip and the extracted text are downloaded at runtime into `downloads/cmapss/` and are never committed. The story export under `demos/cmapss/out/` is gitignored the same way.

## Window recording (V08)

Captured 2026-10-23 with `ffmpeg -f x11grab` on `DISPLAY=:1` (1920×1200), the display this workspace had. Same script the M13 showcase uses, pointed at the FD001 story. Driver log (clock starts when the window's main loop starts; ffmpeg was already grabbing):

```text
$ ./demos/workbench/record_m14_cmapss_showcase.sh
[   1.1s] M14 C-MAPSS FD001 — Workbench story (V01–V08). Data stays out of the repo.
[   7.1s] Open demos/cmapss/story_fd001.m — load, smooth, metrics, heatmap, export
    -> editor /workspace/demos/cmapss/story_fd001.m
[  18.1s] Command Window: dock figures so the Figures panel can show them
    -> DefaultFigureWindowStyle='ans =\n\ndocked'
[  26.9s] V08: Run story_fd001.m — Command Window fills when the script returns
    -> Run returned in 5.6s
    -> figures [(1, 'Figure 1', True), (2, 'Figure 2', True)] focused=2
[  35.2s] V01/V02: FD001 train height, width, units, unit 1 cycles
[  45.2s] V03–V07: metrics, heatmap class, 300 dpi PNG and PDF
[  63.2s] V08: Figures panel — lab figure, then raw and smoothdata
    -> refresh ['1  Figure 1  [docked]', '2  Figure 2  [docked] *'] preview=['Fig 1', 'Fig 2']
[  69.2s] V05/V06: lab figure — tiledlayout, heatmap, Saxena PHM08 footnote
    -> focused=1 list=['1  Figure 1  [docked] *', '2  Figure 2  [docked]']
[  91.9s] V03: last figure — raw, movmean, and gaussian on one axes
    -> focused=2 list=['1  Figure 1  [docked]', '2  Figure 2  [docked] *']
[ 106.6s] M14 story done — export is demos/cmapss/out/ (gitignored). Zenodo CC BY 4.0.
-rw-r--r-- 1 ubuntu ubuntu 3781022 Oct 23 10:03 /workspace/demos/workbench/showcase_m14_cmapss.mp4
120.533333
skip in-repo copy of /workspace/recordings (checkout is /workspace)
```

The Command Window text from that Run (same numbers as the CLI story):

```text
>> set(groot,'DefaultFigureWindowStyle','docked');
>> (run editor)
FD001 train height=20631 width=26 unique_units=100 unit1_cycles=192
V03 dropped sensor_1 sensor_5 sensor_6 sensor_10 sensor_16 sensor_18 sensor_19
V03 unit=1 dropped=7 kept=14 picked=sensor_4 window=15 movmean_agree=0 nlines=3 drop_max=1.36781e-12 keep_min=0.0341246
V04 window=30 sensors=15 same_drop=0
V04 sensor early late delta
V04 sensor_2 642.383 643.383 0.99931
V04 sensor_3 1586.9 1598.81 11.9087
V04 sensor_4 1402.83 1422.96 20.1281
V04 sensor_6 21.6096 21.61 0.000446667
V04 sensor_7 553.948 552.034 -1.91353
V04 sensor_8 2388.06 2388.19 0.130297
V04 sensor_9 9056.06 9087.59 31.5316
V04 sensor_11 47.3561 47.9693 0.613257
V04 sensor_12 521.905 520.278 -1.62719
V04 sensor_13 2388.06 2388.19 0.132977
V04 sensor_14 8137.38 8159.44 22.056
V04 sensor_15 8.41838 8.49808 0.0796948
V04 sensor_17 392.27 395.386 3.116
V04 sensor_20 38.9322 38.5552 -0.377007
V04 sensor_21 23.3592 23.1312 -0.228013
V04 fail_min=128 fail_median=199 fail_max=362 n_units=100 rul0=100 rul_max=361
V04 corr_offmax=0.963157 sensor_14 sensor_9
V04 fft_bin=2 fft_mag=783.392
V05 class=matlab.graphics.chart.HeatmapChart colorbar=on nlabel=15 clim=-1 1
V06 grid=2 3 unit=1 traces=4
V07 png=/workspace/demos/cmapss/out/story_fd001.png pdf=/workspace/demos/cmapss/out/story_fd001.pdf dpi=300
```

Frames taken from the mp4 match those scenes: editor open, Command Window height line, V05–V07 tail, Figure 1 lab preview (traces, heatmap, histogram), Figure 2 raw / smoothdata preview.

```text
$ ffprobe -v error -show_entries stream=width,height,codec_name,duration -of default=nw=1 demos/workbench/showcase_m14_cmapss.mp4
codec_name=h264
width=1920
height=1200
duration=120.533333
```

`/workspace/recordings/` was not written. On this checkout that path is inside the git root; the M13 copy landed outside the repo only when the checkout was `/workspace/openmatlab`. The committed file is `demos/workbench/showcase_m14_cmapss.mp4`.

## Headless proof

`./demos/cmapss/record_story_fd001.sh --headless` does not start ffmpeg and does not write an mp4. It parses the driver, runs the story, and checks the ignore rules.

```text
$ ./demos/cmapss/record_story_fd001.sh --headless
M14 headless proof (no mp4; Workbench capture needs a display)
driver parses; record scripts pass bash -n
/workspace/downloads/cmapss/fd001
FD001 train height=20631 width=26 unique_units=100 unit1_cycles=192
V03 dropped sensor_1 sensor_5 sensor_6 sensor_10 sensor_16 sensor_18 sensor_19
V03 unit=1 dropped=7 kept=14 picked=sensor_4 window=15 movmean_agree=0 nlines=3 drop_max=1.36781e-12 keep_min=0.0341246
V04 window=30 sensors=15 same_drop=0
V04 sensor early late delta
V04 sensor_2 642.383 643.383 0.99931
V04 sensor_3 1586.9 1598.81 11.9087
V04 sensor_4 1402.83 1422.96 20.1281
V04 sensor_6 21.6096 21.61 0.000446667
V04 sensor_7 553.948 552.034 -1.91353
V04 sensor_8 2388.06 2388.19 0.130297
V04 sensor_9 9056.06 9087.59 31.5316
V04 sensor_11 47.3561 47.9693 0.613257
V04 sensor_12 521.905 520.278 -1.62719
V04 sensor_13 2388.06 2388.19 0.132977
V04 sensor_14 8137.38 8159.44 22.056
V04 sensor_15 8.41838 8.49808 0.0796948
V04 sensor_17 392.27 395.386 3.116
V04 sensor_20 38.9322 38.5552 -0.377007
V04 sensor_21 23.3592 23.1312 -0.228013
V04 fail_min=128 fail_median=199 fail_max=362 n_units=100 rul0=100 rul_max=361
V04 corr_offmax=0.963157 sensor_14 sensor_9
V04 fft_bin=2 fft_mag=783.392
V05 class=matlab.graphics.chart.HeatmapChart colorbar=on nlabel=15 clim=-1 1
V06 grid=2 3 unit=1 traces=4
V07 png=/workspace/demos/cmapss/out/story_fd001.png pdf=/workspace/demos/cmapss/out/story_fd001.pdf dpi=300
.gitignore:10:downloads/	downloads/cmapss/CMAPSSData.zip
.gitignore:10:downloads/	downloads/cmapss/fd001/train_FD001.txt
.gitignore:99:demos/cmapss/out/	demos/cmapss/out/story_fd001.png
.gitignore:99:demos/cmapss/out/	demos/cmapss/out/story_fd001.pdf
png bytes 666789
pdf bytes 48068
b'%PDF-1.4'
headless proof done; no mp4 written
```

`git ls-files downloads/cmapss demos/cmapss/out` printed nothing.

## Reproduce from tip main and Zenodo

From a fresh clone, with network once for the zip:

```text
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
openmatlab -e "run('demos/cmapss/story_fd001.m')"
```

The Workbench capture also needs an X display and `python3-tk`:

```text
DISPLAY=:2 ./demos/cmapss/record_story_fd001.sh
```

That execs `demos/workbench/record_m14_cmapss_showcase.sh`. `--dry-run` skips ffmpeg and still opens the window. `--headless` is the proof above. No MathWorks file is required.

## Obstacle table (V10)

| Item | Story blocker? | Note |
|---|---|---|
| Milestone/9 Core backlog | no | Not emptied. No issue labelled `m14-blocker`. |
| M12 corpus residuals | no | Out of this vertical. The FD001 story does not run the corpus. |
| MIT-BIH, CWRU | no | Not on the path. Not vendored. |
| `zscore`, `pspectrum`, `datetime`, FD002–FD004 | no | Milestone non-goals. The story uses `normalize(...,'zscore')`, `fft`, and cycles. |

```text
$ gh issue list --label m14-blocker --state all --limit 20
(no output, exit 0)
```

## Measurable gate: pytest

The command CI runs. Exit code 0. Elapsed 209.53s. The progress meter reached 100%. Its glyphs are 2257 `.` and 1 `s` (the usual "N passed" sentence was not printed under `-q` with the coverage report).

```text
$ python -m pytest -m "unit or bdd" --cov=openmatlab --cov-report=term-missing --cov-fail-under=60 --tb=line -q
Required test coverage of 60% reached. Total coverage: 77.96%
```

**Existing tests changed: none.** No new feature-map row. This epic adds the recording path and the acceptance package, not a new language capability.

## Feature map

Unchanged. `libs.graphics.figio` stays `done`. `libs.graphics.heatmap`, `libs.cmapss_fd001`, and `libs.cmapss_metrics` stay `partial` as in #994–#998.

## Residuals

No new residual. Corpus burn-down, milestone/9, MIT-BIH, and CWRU stay out of this epic. The product's 60s debugger wait is unchanged; the driver raises it to 180s in the recording process only.

## Milestone progress (M14)

- Criteria met: **10 / 10** (V01–V10) in [`M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md). V01 and V02 are **met**; their evidence is [EPIC-994](EPIC-994.md). V08, V09, and V10 are **met** in this package.
- Per-epic evidence: [EPIC-994](EPIC-994.md), [EPIC-995](EPIC-995.md), [EPIC-996](EPIC-996.md), [EPIC-997](EPIC-997.md), [EPIC-998](EPIC-998.md), this file.
- Milestone/14 is **closed**. Shaw accepted epics #994–#999 on 2026-10-23 (Asia/Shanghai).

## CI

Required check `test` is the PR check. The URL is added when that run finishes.
