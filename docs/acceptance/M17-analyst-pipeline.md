# M17 Analyst pipeline — acceptance package

**Milestone:** [M17 Analyst pipeline](https://github.com/superche/openmatlab/milestone/17) · [`docs/milestones/M17-analyst-pipeline.md`](../milestones/M17-analyst-pipeline.md)  
**Epic:** [#1032](https://github.com/superche/openmatlab/issues/1032)  
**Story issue:** [#1034](https://github.com/superche/openmatlab/issues/1034)  
**Captured:** 2026-11-01  
**Rule:** The recording is a real Workbench window (`ffmpeg` `x11grab`). Numbers are copied from command output. The assay CSV in the repository is synthetic.

**Not closed.** The criteria table is **6 / 6** evidenced on this branch and **2 / 6** on `main` (A01, A02). A03 waits on PR #1057. A04 and A05 wait on this branch merging after that. Epic #1032 stays open.

## 中文摘要

一份合成的野外含水率记录在 Workbench 里跑通。`readtable` 把 `NA`、`-999` 和空字段当成缺失。Command Window 打出 12 行、9 个缺失单元格，删掉 2 行没有站点的记录，用 `previous` 补上 2 个温度、用 `constant` `'pass'` 补上 2 个质控，再删掉 3 行仍然没有含水率的记录。`groupsummary` 带 `'IncludeEmptyGroups'`：North / South / East 有均值，West 的计数是 0、均值是 NaN。结果 CSV 写到 `demos/analyst/out/`，生成文件不入库。录屏是 `demos/workbench/showcase_m17_analyst.mp4`（57.4 秒，1920×1200）。不把验收绑在语料百分比上，也不清 milestone/9。没有 `m17-blocker`。xlsx 不是这条路径。

## Video

| File | Duration | What it shows |
|---|---|---|
| [`demos/workbench/showcase_m17_analyst.mp4`](../../demos/workbench/showcase_m17_analyst.mp4) | 57.4 s, 1920×1200, H.264, 2576379 bytes | Editor opens `story_assays.m`. Command Window prints the missing counts, the four groups (West count 0, means NaN), and the two CSV paths. |

Re-record: `DISPLAY=:2 ./demos/workbench/record_m17_analyst_showcase.sh`  
This capture used `DISPLAY=:1` because that was the display on the machine.  
Driver: [`demos/workbench/m17_driver.py`](../../demos/workbench/m17_driver.py)  
Story entry: [`demos/analyst/record_story_assays.sh`](../../demos/analyst/record_story_assays.sh)  
No display: `./demos/analyst/record_story_assays.sh --headless` (CLI proof, no mp4).

Per-issue evidence for the story: [EPIC-1034](EPIC-1034.md).

## Children

| Issue | Role | On `main`? |
|---|---|---|
| [#1033](https://github.com/superche/openmatlab/issues/1033) | `ismissing` / `rmmissing` / `fillmissing` `constant` `previous` `next`. Review fixes [#1039](https://github.com/superche/openmatlab/issues/1039). | yes, closed |
| [#721](https://github.com/superche/openmatlab/issues/721) | CSV `'TreatAsMissing'`. xlsx stays an error ([#1049](https://github.com/superche/openmatlab/issues/1049)). | yes, closed |
| [#742](https://github.com/superche/openmatlab/issues/742) | `IncludeEmptyGroups` for the story. Other bullets are #1052 #1053 #1054 #1055 #1056 on the Core backlog. | no, PR [#1057](https://github.com/superche/openmatlab/pull/1057) |
| [#1034](https://github.com/superche/openmatlab/issues/1034) | `demos/analyst`, `out/` convention, this package. | no, this branch |
| [#1035](https://github.com/superche/openmatlab/issues/1035) | Docs sync. Does not block exit. | yes, closed |

## Reproduce

A third party needs the tip that contains this branch and #1057, and a Python 3.10+ environment. No MathWorks binary. No network. Story: [`demos/analyst/story_assays.m`](../../demos/analyst/story_assays.m). Data: [`demos/analyst/assays.csv`](../../demos/analyst/assays.csv) (synthetic, MIT, committed).

```text
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
openmatlab -e "run('demos/analyst/story_assays.m')"
```

The measured lines are in [EPIC-1034](EPIC-1034.md). West's `GroupCount` is 0 and both means are NaN. The summary CSV is 166 bytes. The cleaned CSV is 197 bytes. Neither file is committed.

## `out/` convention

`demos/analyst/out/README.md` is tracked and states the rule. `.gitignore` ignores every other file in that directory. The script creates the directory if it is missing. Do not commit `site_summary.csv` or `cleaned.csv`.

## Obstacle table

| Item | Blocks close? |
|---|---|
| Milestone/9 | No. It is not required to be empty. No `m17-blocker` issue. |
| M12 corpus residuals | No. The story does not read the corpus and does not require a pass-rate change. |
| xlsx | No. Explicit non-goal. `readtable` still rejects a spreadsheet. |
| `fillmissing` beyond `constant` / `previous` / `next` | No. Explicit non-goal. |
| #742 leftovers (#1052–#1056) | No. They are on the Core backlog, outside this epic's In list. |
| #1057 not merged | Yes, for a `main` one-shot. A03 is not on `main` until that PR merges. This branch is based on it. |
| This branch not merged | Yes, for a `main` one-shot. A04 and A05 land with it. |

## Out of scope, confirmed

xlsx. `detectImportOptions`. The rest of the fill-method matrix. A fourth vertical. Corpus percentage. Clearing milestone/9. Editing an existing test (none were edited).

## CI

Required check `test`. This branch has no pull request yet, so there is no Actions URL. The URL is reported when a PR exists and the check finishes.
