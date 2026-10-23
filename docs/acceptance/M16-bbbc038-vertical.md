# M16 BBBC038 nuclei image vertical — acceptance package

**Milestone:** [BBBC038 nuclei image vertical](https://github.com/superche/openmatlab/milestone/16) · [`docs/milestones/M16-bbbc038-vertical.md`](../milestones/M16-bbbc038-vertical.md)  
**Opened:** 2026-10-23 (Asia/Shanghai), Shaw approved the Defaults as a block.  
**Captured:** 2026-10-23  
**Rule:** The recording is a real Workbench window (`ffmpeg` `x11grab`). Numbers are copied from command output. The Broad zip and the PNGs are not in the repository. Epics #1020–#1025 stay open until Shaw accepts them. Milestone/16 stays open.

**Ready for batch acceptance.** The milestone table is **10 / 10** (V01–V10 met). This file is the package a reviewer can read once. Each epic still has its own evidence file. Closing the epics and the milestone is Shaw's step.

## 中文摘要

`stage1_test` 的一个 FOV 在 Workbench 里跑通：Current Folder 打开 `story_stage1_test.m`，Command Window 打出 `count=6`、平均面积 163、中位数 153，以及 V01–V07。Figures 面板先显示原图对掩膜，再显示面积直方图，然后显示重新打开的 2×2 组会图（叠加、直方图、计数摘要）。录屏是 [`demos/workbench/showcase_m16_bbbc038.mp4`](../../demos/workbench/showcase_m16_bbbc038.mp4)（140.1 秒，1920×1200）。数据 CC0 1.0，引用 Caicedo 等 Nature Methods 2019（doi:10.1038/s41592-019-0612-7）和 BBBC038v1。`stage1_test.zip` 和 FOV PNG 不入库。语料残留和 milestone/9 不挡住关闭。没有 `m16-blocker`。门禁表 **10 / 10**。Epic #1020–#1025 与 milestone/16 保持打开，等 Shaw 批量验收。

## Video (V08)

| File | Duration | What it shows |
|---|---|---|
| [`demos/workbench/showcase_m16_bbbc038.mp4`](../../demos/workbench/showcase_m16_bbbc038.mp4) | 140.1 s, 1920×1200, H.264, 4359513 bytes | Editor opens the story. Command Window prints `count=6`, `mean=163.0000`, `median=153.0000`, and the V01–V07 lines, including the 300 dpi PNG and PDF paths. Figures panel lists the docked figures and previews Fig 1 (raw / mask), Fig 2 (area histogram), then Fig 3 (2×2 lab chart, reopened after export). |

Re-record: `DISPLAY=:2 ./demos/workbench/record_m16_bbbc038_showcase.sh`  
Driver: [`demos/workbench/m16_driver.py`](../../demos/workbench/m16_driver.py)  
Story entry: [`demos/bbbc038/record_story_stage1_test.sh`](../../demos/bbbc038/record_story_stage1_test.sh)  
No display: `./demos/bbbc038/record_story_stage1_test.sh --headless` (CLI proof, no mp4).

Scene clock from the driver log in [EPIC-1025](EPIC-1025.md). Frames read back from the file match the editor, the count / mean-area lines, the raw / mask preview, the histogram, and the lab preview.

## Per-epic evidence

| Epic | Criteria | Evidence |
|---|---|---|
| [#1020](https://github.com/superche/openmatlab/issues/1020) I-E1 | V01, V02 | [EPIC-1020](EPIC-1020.md) |
| [#1021](https://github.com/superche/openmatlab/issues/1021) I-E2 | V03 | [EPIC-1021](EPIC-1021.md) |
| [#1022](https://github.com/superche/openmatlab/issues/1022) I-E3 | V04, V05 | [EPIC-1022](EPIC-1022.md) |
| [#1023](https://github.com/superche/openmatlab/issues/1023) I-E4 | V06 | [EPIC-1023](EPIC-1023.md) |
| [#1024](https://github.com/superche/openmatlab/issues/1024) I-E5 | V07 | [EPIC-1024](EPIC-1024.md) |
| [#1025](https://github.com/superche/openmatlab/issues/1025) I-E6 | V08, V09, V10 | [EPIC-1025](EPIC-1025.md) |

The milestone table marks **10 / 10** met (V01–V10). The epics stay open.

## Licence and citation

- **Data.** Broad Bioimage Benchmark Collection, BBBC038v1, `stage1_test.zip` only. Landing page https://bbbc.broadinstitute.org/BBBC038. Licence **CC0 1.0**. URL locked in `demos/bbbc038/manifest.json`: `https://data.broadinstitute.org/bbbc/BBBC038/stage1_test.zip`. Size 9545388. sha256 `c097954151884341448a5c77aab21f581815ad9cad203ff2ff38d6947c9f0733`.
- **Citation.** Caicedo, J. C., et al. (2019). Nucleus segmentation across imaging experiments: the 2018 Data Science Bowl. Nature Methods 16:1247–1253. doi:[10.1038/s41592-019-0612-7](https://doi.org/10.1038/s41592-019-0612-7).
- **Not committed.** The zip and the demo FOV PNG live under `downloads/bbbc038/` (gitignored). The story PNG and PDF live under `demos/bbbc038/out/` (gitignored). The repository holds the manifest (size and sha256) and the scripts.

## Reproduce (V09)

A third party needs tip `main`, a Python 3.10+ environment, and network access to Broad once. No MathWorks binary. Story entry: [`demos/bbbc038/story_stage1_test.m`](../../demos/bbbc038/story_stage1_test.m). Helper: [`demos/bbbc038/load_fov.m`](../../demos/bbbc038/load_fov.m).

```text
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
openmatlab -e "run('demos/bbbc038/story_stage1_test.m')"
```

That prints the V01–V07 lines. On this workspace the measured lines are in [EPIC-1025](EPIC-1025.md): `bytes=9545388`, `size=256 256 3 class=uint8`, `count=6`, `mean=163.0000`, `median=153.0000`, `V06 grid=2 2 tiles=4`, and a non-empty 300 dpi PNG and PDF.

Workbench window (X display, `ffmpeg`, `xdotool`, and `python3-tk`):

```text
DISPLAY=:2 ./demos/bbbc038/record_story_stage1_test.sh
```

The headless proof printed the same V01–V07 lines, `png bytes 258791`, `pdf bytes 114842`, and `git check-ignore` hits on the zip, the FOV PNG, and both export files. `git ls-files` of those directories was empty. Full transcript: [EPIC-1025](EPIC-1025.md).

## Obstacle table (V10)

| Item | Blocks close? |
|---|---|
| Milestone/9 | No. It is not required to be empty. No `m16-blocker` issue. |
| M12 corpus residuals / demilestone burn-down | No. The story does not depend on a corpus percentage. |
| C-MAPSS | No. Milestone/14 stays closed. This vertical does not reopen it. |
| MIT-BIH | No. This vertical does not reopen it. |
| `stage1_train`, a contest entry, a full Image Processing Toolbox, App Designer | No. Milestone non-goals. One FOV from `stage1_test.zip` only. |

## Timeline

| Date | What |
|---|---|
| 2026-10-23 | Milestone/16 opened. Epics [#1020](https://github.com/superche/openmatlab/issues/1020)–[#1025](https://github.com/superche/openmatlab/issues/1025). Defaults locked: `stage1_test.zip` only, runtime download, no committed bytes. |
| 2026-10-23 | I-E1 landed. V01 and V02 evidence: [EPIC-1020](EPIC-1020.md). |
| 2026-10-23 | I-E2 landed. V03 evidence: [EPIC-1021](EPIC-1021.md). Global Otsu plus `bwareaopen` (`P = 50`) and a 1-by-2 before/after panel. |
| 2026-10-23 | I-E3 landed. V04 and V05 evidence: [EPIC-1022](EPIC-1022.md). Count 6, mean area 163, median 153, area histogram on its own figure. |
| 2026-10-23 | I-E4 landed. V06 evidence: [EPIC-1023](EPIC-1023.md). 2×2 lab figure with `labeloverlay`, area histogram, summary, and the CC0 / Caicedo 2019 / BBBC038v1 footnote. |
| 2026-10-23 | I-E5 landed. V07 evidence: [EPIC-1024](EPIC-1024.md). 300 dpi PNG and PDF of that lab figure. The crop keeps the title and the footnote. |
| 2026-10-23 | I-E6 landed. V08, V09, and V10 evidence: [EPIC-1025](EPIC-1025.md). Workbench recording is `showcase_m16_bbbc038.mp4`. Epics stay open. |

## Out of scope, confirmed

Simulink, Stateflow, App Designer, `uifigure`. A full Image Processing Toolbox. `stage1_train` and a Kaggle contest entry. Corpus pass rate as this vertical's gate. Pixel parity with MATLAB. `export_fig` and animation. Editing existing tests (none were edited).

## CI

Required check `test` on the packaging PR. The URL is reported with the merge.
