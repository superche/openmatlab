# M15 MIT-BIH Arrhythmia vertical — acceptance package

**Milestone:** [MIT-BIH Arrhythmia vertical](https://github.com/superche/openmatlab/milestone/15) · [`docs/milestones/M15-mitbih-vertical.md`](../milestones/M15-mitbih-vertical.md)  
**Opened:** 2026-10-23 (Asia/Shanghai), Shaw approved the Defaults as a block.  
**Captured:** 2026-10-23  
**Rule:** The recording is a real Workbench window (`ffmpeg` `x11grab`). Numbers are copied from command output. Raw PhysioNet files are not in the repository. Epics #1008–#1013 stay open until Shaw accepts them. Milestone/15 stays open.

**Ready for batch acceptance.** The milestone table is **10 / 10** (V01–V10 met). This file is the package a reviewer can read once. Each epic still has its own evidence file. Closing the epics and the milestone is Shaw's step.

## 中文摘要

记录 100 的故事在 Workbench 里跑通：Current Folder 打开 `story_record100.m`，Command Window 打出 `Fs=360`、峰数 2273、平均 RR 0.794594 s，以及 V03–V07。Figures 面板先显示 2×2 实验室图，再显示原始对滤波的最后一张图。录屏是 [`demos/workbench/showcase_m15_mitbih.mp4`](../../demos/workbench/showcase_m15_mitbih.mp4)（122.6 秒，1920×1200）。数据 ODC-By 1.0，DOI 10.13026/C2F305，引用 Moody & Mark IEEE EMB 2001 和 Goldberger 等 Circulation 2000。`.hea` / `.dat` / `.atr` 不入库。语料残留和 milestone/9 不挡住关闭。没有 `m15-blocker`。门禁表 **10 / 10**。Epic #1008–#1013 与 milestone/15 保持打开，等 Shaw 批量验收。

## Video (V08)

| File | Duration | What it shows |
|---|---|---|
| [`demos/workbench/showcase_m15_mitbih.mp4`](../../demos/workbench/showcase_m15_mitbih.mp4) | 122.6 s, 1920×1200, H.264, 2761557 bytes | Editor opens the story. Command Window prints `Fs=360`, `peaks=2273`, `mean_rr=0.794594`, and the V03–V07 lines, including the 300 dpi PNG and PDF paths. Figures panel lists five docked figures and previews Fig 4 (2×2 lab chart) then Fig 5 (raw / filtered). |

Re-record: `DISPLAY=:2 ./demos/workbench/record_m15_mitbih_showcase.sh`  
Driver: [`demos/workbench/m15_driver.py`](../../demos/workbench/m15_driver.py)  
Story entry: [`demos/mitbih/record_story_record100.sh`](../../demos/mitbih/record_story_record100.sh)  
No display: `./demos/mitbih/record_story_record100.sh --headless` (CLI proof, no mp4).

Scene clock from the driver log in [EPIC-1013](EPIC-1013.md). Frames read back from the file match the editor, the Fs / mean-RR lines, the lab preview, and the raw / filtered preview.

## Per-epic evidence

| Epic | Criteria | Evidence |
|---|---|---|
| [#1008](https://github.com/superche/openmatlab/issues/1008) B-E1 | V01, V02 | [EPIC-1008](EPIC-1008.md) |
| [#1009](https://github.com/superche/openmatlab/issues/1009) B-E2 | V03 | [EPIC-1009](EPIC-1009.md) |
| [#1010](https://github.com/superche/openmatlab/issues/1010) B-E3 | V04, V05 | [EPIC-1010](EPIC-1010.md) |
| [#1011](https://github.com/superche/openmatlab/issues/1011) B-E4 | V06 | [EPIC-1011](EPIC-1011.md) |
| [#1012](https://github.com/superche/openmatlab/issues/1012) B-E5 | V07 | [EPIC-1012](EPIC-1012.md) |
| [#1013](https://github.com/superche/openmatlab/issues/1013) B-E6 | V08, V09, V10 | [EPIC-1013](EPIC-1013.md) |

The milestone table marks **10 / 10** met (V01–V10). The epics stay open.

## Licence and citation

- **Data.** PhysioNet MIT-BIH Arrhythmia Database, record 100, version 1.0.0. DOI [10.13026/C2F305](https://doi.org/10.13026/C2F305). Licence **ODC-By 1.0**. URLs locked in `demos/mitbih/manifest.json`: `https://physionet.org/files/mitdb/1.0.0/100.hea`, `100.dat`, and `100.atr`.
- **Citation.** Moody, G. B., and Mark, R. G. (2001). IEEE Engineering in Medicine and Biology Magazine, 20(3):45–50. Goldberger, A. L., et al. (2000). Circulation 101(23):e215–e220.
- **Not committed.** `100.hea`, `100.dat`, and `100.atr` live under `downloads/mitbih/` (gitignored). The story PNG and PDF live under `demos/mitbih/out/` (gitignored). The repository holds the manifest (size and sha256) and the scripts.

## Reproduce (V09)

A third party needs tip `main`, a Python 3.10+ environment, and network access to PhysioNet once. No MathWorks binary. Story entry: [`demos/mitbih/story_record100.m`](../../demos/mitbih/story_record100.m). Helper: [`demos/mitbih/load_record100.m`](../../demos/mitbih/load_record100.m).

```text
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
openmatlab -e "run('demos/mitbih/story_record100.m')"
```

That prints the V01–V07 lines. On this workspace the measured lines are in [EPIC-1013](EPIC-1013.md): `Fs=360`, `peaks=2273`, `mean_rr=0.794594`, `V06 grid=2 2 tiles=4`, and a non-empty 300 dpi PNG and PDF.

Workbench window (X display, `ffmpeg`, `xdotool`, and `python3-tk`):

```text
DISPLAY=:2 ./demos/mitbih/record_story_record100.sh
```

The headless proof printed the same V01–V07 lines, `png bytes 636564`, `pdf bytes 59570`, and `git check-ignore` hits on the three PhysioNet files and both export files. `git ls-files` of those directories was empty. Full transcript: [EPIC-1013](EPIC-1013.md).

## Obstacle table (V10)

| Item | Blocks close? |
|---|---|
| Milestone/9 | No. It is not required to be empty. No `m15-blocker` issue. |
| M12 corpus residuals / demilestone burn-down | No. The story does not depend on a corpus percentage. |
| C-MAPSS | No. Milestone/14 stays closed. This vertical does not reopen it. |
| Other MIT-BIH records, a WFDB toolbox, an arrhythmia classifier, App Designer | No. Milestone non-goals. Record 100 only. |

## Timeline

| Date | What |
|---|---|
| 2026-10-23 | Milestone/15 opened. Epics [#1008](https://github.com/superche/openmatlab/issues/1008)–[#1013](https://github.com/superche/openmatlab/issues/1013). Defaults locked: record 100 only, runtime download, no committed bytes. |
| 2026-10-23 | B-E1 landed. V01 and V02 evidence: [EPIC-1008](EPIC-1008.md). |
| 2026-10-23 | B-E2 landed. V03 evidence: [EPIC-1009](EPIC-1009.md). |
| 2026-10-23 | B-E3 landed. V04 and V05 evidence: [EPIC-1010](EPIC-1010.md). |
| 2026-10-23 | B-E4 landed. V06 evidence: [EPIC-1011](EPIC-1011.md). |
| 2026-10-23 | B-E5 landed. V07 evidence: [EPIC-1012](EPIC-1012.md). |
| 2026-10-23 | B-E6 landed. V08, V09, and V10 evidence: [EPIC-1013](EPIC-1013.md). Workbench recording is `showcase_m15_mitbih.mp4`. Epics stay open. |

## Out of scope, confirmed

Simulink, Stateflow, App Designer, `uifigure`. A full WFDB toolbox. Any MIT-BIH record other than 100. Corpus pass rate as this vertical's gate. Pixel parity with MATLAB. `export_fig` and animation. Editing existing tests (none were edited).

## CI

Required check `test` on the packaging PR. The URL is reported with the merge.
