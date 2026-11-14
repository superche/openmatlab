# C-MAPSS FD001 (M14 V-E1)

## What this demo is

This directory analyzes published NASA C-MAPSS FD001 tables. A runtime download from Zenodo places `train_FD001.txt`, `test_FD001.txt`, and `RUL_FD001.txt` in a gitignored cache. `story_fd001.m` then filters, summarizes, and plots those columns. It does not integrate an engine model, and it does not generate the FD001 time series.

The citation below names the source paper. That paper's title contains the word Simulation. The commands in this directory read the published files.

[中文](#这个演示是什么). Milestone intent: [`docs/milestones/M14-cmapss-vertical.md`](../../docs/milestones/M14-cmapss-vertical.md#intent).

## 这个演示是什么

本目录分析已发表的 NASA C-MAPSS FD001 表。从 Zenodo 的运行时下载把 `train_FD001.txt`、`test_FD001.txt` 和 `RUL_FD001.txt` 放进被 gitignore 的缓存。`story_fd001.m` 接着过滤、汇总并绘制这些列。它不对发动机模型做积分，也不生成 FD001 时间序列。

下面的引文给出源论文。该论文标题里有 Simulation 一词。本目录中的命令读取已发表的文件。

[English](#what-this-demo-is). 里程碑意图：[`docs/milestones/M14-cmapss-vertical.md`](../../docs/milestones/M14-cmapss-vertical.md#intent)。

Runtime download of NASA C-MAPSS from Zenodo and a `readtable` load of FD001.
The zip and the extracted text are cached under `downloads/cmapss/` and are
not part of the repository.

Citation: A. Saxena, K. Goebel, D. Simon, and N. Eklund, "Damage Propagation
Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08, 2008.
Data: DOI 10.5281/zenodo.15346912 (CC BY 4.0).

From the repository root:

```text
openmatlab -e "run('demos/cmapss/story_fd001.m')"
```

`load_fd001('train'|'test'|'rul')` is the script a MATLAB user would write:
space delimiter, no header, PHM08 names (`unit`, `cycle`, three settings,
21 sensors). `python -m openmatlab.libs.cmapss fetch` only fills the cache.

`story_fd001.m` then keeps unit 1, drops sensor columns whose sample standard
deviation is at most `1e-6`, and plots that unit's busiest remaining channel
with `smoothdata(...,'movmean',15)` and `smoothdata(...,'gaussian',15)` on the
same axes (M14 V03).

It also prints a short FD001 train metric table (M14 V04): per-unit failure
cycle and train RUL (`max(cycle) - cycle`, from `groupsummary`), early versus
late means on the first and last 30 cycles, and the Pearson correlation of the
sensors that are not idle. The lab-meeting figure (M14 V05, V06) is one
`tiledlayout(2, 3)`: unit 1 sensor traces, early versus late, a `heatmap` of
the correlation down the right column (colorbar, sensor tick labels), the
failure-cycle histogram, and unit 1's RUL. The layout title carries the unit
id. The layout xlabel is the footnote (Saxena PHM08 and Zenodo DOI
10.5281/zenodo.15346912). The raw / `smoothdata` axes is still drawn after
that, so it stays the last figure. A single-channel `fft` line is a demo bonus.

The same run writes the lab figure to `demos/cmapss/out/story_fd001.png` and
`story_fd001.pdf` at 300 dpi (M14 V07). That directory is gitignored. The
default `exportgraphics` resolution, when a script does not pass one, is 150 dpi.

Workbench recording (M14 V08) uses the M13 showcase pattern. From the
repository root, with a display:

```text
DISPLAY=:2 ./demos/cmapss/record_story_fd001.sh
```

That execs `demos/workbench/record_m14_cmapss_showcase.sh` and
`demos/workbench/m14_driver.py`. The window opens this directory, runs
`story_fd001.m`, and shows the Command Window lines and the Figures panel.
`--dry-run` skips ffmpeg. Without a display, `--headless` runs the story in
the CLI and writes no mp4. The video, when captured, is
`demos/workbench/showcase_m14_cmapss.mp4`.
