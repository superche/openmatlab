# M14 C-MAPSS PHM vertical — batch acceptance

**Milestone:** [C-MAPSS PHM vertical](https://github.com/superche/openmatlab/milestone/14) · [`docs/milestones/M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md)  
**Captured:** 2026-10-23  
**Rule:** The recording is a real Workbench window (`ffmpeg` `x11grab`). Numbers are copied from command output. The C-MAPSS zip and text are not in the repository.

**Accepted.** Shaw accepted epics **#994–#999** on 2026-10-23 (Asia/Shanghai). Milestone/14 is **closed**. This file is the batch a reviewer can read once. Each epic still has its own evidence file.

## 中文摘要

FD001 故事在 Workbench 里跑通：Current Folder 打开 `story_fd001.m`，Command Window 打出训练集规模和 V03–V07 指标，Figures 面板先显示组会用的多面板图（含 `heatmap`），再显示 raw / `smoothdata` 曲线。录屏是 `demos/workbench/showcase_m14_cmapss.mp4`（约 121 秒，1920×1200）。数据来自 Zenodo CC BY 4.0（DOI 10.5281/zenodo.15346912），引用 Saxena PHM08，zip 和原文不入库。语料残留和 milestone/9 不挡住本垂直关闭。没有 `m14-blocker` issue。Shaw 于 2026-10-23（Asia/Shanghai）验收 #994–#999，milestone/14 已关闭。门禁表 **10 / 10**，V01 与 V02 为 met。

## Video (V08)

| File | Duration | What it shows |
|---|---|---|
| [`demos/workbench/showcase_m14_cmapss.mp4`](../../demos/workbench/showcase_m14_cmapss.mp4) | 120.5 s, 1920×1200, H.264, 3781022 bytes | Editor opens the story. Command Window prints `height=20631` and the V03–V07 lines, including the 300 dpi PNG and PDF paths. Figures panel lists two docked figures and previews Fig 1 (lab chart) then Fig 2 (raw / smoothdata). |

Re-record: `DISPLAY=:2 ./demos/workbench/record_m14_cmapss_showcase.sh`  
Driver: [`demos/workbench/m14_driver.py`](../../demos/workbench/m14_driver.py)  
Story entry: [`demos/cmapss/record_story_fd001.sh`](../../demos/cmapss/record_story_fd001.sh)  
No display: `./demos/cmapss/record_story_fd001.sh --headless` (CLI proof, no mp4).

Scene clock from the driver log in [EPIC-999](EPIC-999.md). Frames read back from the file match the editor, the height line, the V05–V07 tail, the lab preview, and the smoothdata preview.

## Per-epic evidence

| Epic | Criteria | Evidence |
|---|---|---|
| [#994](https://github.com/superche/openmatlab/issues/994) V-E1 | V01, V02 | [EPIC-994](EPIC-994.md) |
| [#995](https://github.com/superche/openmatlab/issues/995) V-E2 | V03 | [EPIC-995](EPIC-995.md) |
| [#996](https://github.com/superche/openmatlab/issues/996) V-E3 | V04 | [EPIC-996](EPIC-996.md) |
| [#997](https://github.com/superche/openmatlab/issues/997) V-E4 | V05, V06 | [EPIC-997](EPIC-997.md) |
| [#998](https://github.com/superche/openmatlab/issues/998) V-E5 | V07 | [EPIC-998](EPIC-998.md) |
| [#999](https://github.com/superche/openmatlab/issues/999) V-E6 | V08, V09, V10 | [EPIC-999](EPIC-999.md) |

The milestone table marks **10 / 10** met (V01–V10). V01 and V02 are **met**; the evidence is EPIC-994.

## Licence and citation

- **Data.** NASA C-MAPSS, Zenodo record 15346912, DOI 10.5281/zenodo.15346912, licence **CC BY 4.0**. URL locked in `demos/cmapss/manifest.json`: `https://zenodo.org/records/15346912/files/CMAPSSData.zip?download=1`.
- **Citation.** A. Saxena, K. Goebel, D. Simon, and N. Eklund, "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08, 2008.
- **Not committed.** The zip and `train_FD001.txt` / `test_FD001.txt` / `RUL_FD001.txt` live under `downloads/cmapss/` (gitignored). The story PNG and PDF live under `demos/cmapss/out/` (gitignored). The repository holds the manifest (size and sha256) and the scripts.

## Reproduce (V09)

A third party needs tip `main`, a Python 3.10+ environment, and network access to Zenodo. No MathWorks binary.

```text
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
openmatlab -e "run('demos/cmapss/story_fd001.m')"
```

Workbench window (X display and `python3-tk`):

```text
DISPLAY=:2 ./demos/cmapss/record_story_fd001.sh
```

The headless proof on this workspace printed `FD001 train height=20631 width=26 unique_units=100 unit1_cycles=192`, the V03–V07 lines, `png bytes 666789`, `pdf bytes 48068`, and `git check-ignore` hits on the zip, the train text, and both export files. `git ls-files` of those directories was empty. Full transcript: [EPIC-999](EPIC-999.md).

## Obstacle table (V10)

| Item | Blocks close? |
|---|---|
| Milestone/9 | No. It is not required to be empty. No `m14-blocker` issue. |
| M12 corpus residuals / demilestone burn-down | No. The story does not depend on a corpus percentage. |
| MIT-BIH, CWRU | No. Not on the path, not vendored. |
| `zscore`, `pspectrum`, full `smoothdata` / `heatmap` matrices, FD002–FD004, contest RUL models | No. Milestone non-goals. The story uses `normalize(...,'zscore')`, `fft`, FD001 only. |

## Out of scope, confirmed

Simulink, Stateflow, App Designer, `uifigure`. Toolbox parity (Signal Processing, Predictive Maintenance, Prognostics). Corpus pass rate as this vertical's gate. Pixel parity with MATLAB and MATLAB `.fig` binary compatibility. `export_fig` and animation. Deep-learning RUL. Editing existing tests (none were edited).

## CI

Required check `test` on the packaging PR. The URL is added on [EPIC-999](EPIC-999.md) when that run finishes.
