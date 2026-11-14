# OpenMATLAB / 开源 MATLAB 兼容实现

**English** | [中文](#中文)

## English

**OpenMATLAB** is a clean-room, open-source MATLAB-compatible **matrix-first
workbench** (language + runtime + libs), built from **public specs** — not from
proprietary MATLAB binaries.

### Status (v0.0.2+ — post-MVP workbench)

Milestone close-outs (GitHub, checked 2026-10-31): Workbench MVP (M1), Octave-breadth (M2, 19/19 criteria), M3 domain criteria (7/7,
close-out 2026-10-16; `docs/milestones/M3-domain-toolboxes.md`), Plugin host (M4), Domain business-conformance (M5),
MATLAB-aligned Workbench (M6), MATLAB core language & I/O (M7, 11/11 criteria, closed 2026-10-13;
`docs/milestones/M7-core-language-io.md`), Object system (M8, 10/10 criteria, closed 2026-10-16;
`docs/milestones/M8-object-system.md`), Tables and data types (M10, 10/10, closed 2026-10-16; `docs/milestones/M10-tables.md`), Debugger and Workbench (M11, 10/10, closed 2026-10-16; `docs/milestones/M11-debugger-workbench.md`), Real-script compatibility gate (M12, 10/10, closed 2026-10-23; `docs/milestones/M12-corpus-gate.md`), Graphics completion (M13, 10/10, closed 2026-10-23; `docs/milestones/M13-graphics.md`), C-MAPSS PHM vertical (M14, 10/10, closed 2026-10-23; `docs/milestones/M14-cmapss-vertical.md`), MIT-BIH Arrhythmia vertical (M15, 10/10, closed 2026-10-23; `docs/milestones/M15-mitbih-vertical.md`), BBBC038 nuclei image vertical (M16, 10/10, closed 2026-10-25; `docs/milestones/M16-bbbc038-vertical.md`). Open: Core backlog (milestone/9, p2 residuals; `docs/GAP-ANALYSIS.md`) and M17 Analyst pipeline (milestone/17, open; missing values × CSV import slice × groupsummary story cut × `demos/analyst`; criteria `docs/milestones/M17-analyst-pipeline.md`). Vertical demos: `demos/cmapss`, `demos/mitbih`, `demos/bbbc038`. Works today: matrix REPL (`-e` / bare), NumPy arrays, control
flow, scripts and `.m` functions, cells, `addpath`/`which`, handle graphics (figure/axes/get/set, hold, subplot, saveas), try/catch, varargin, file I/O and save/load, containers.Map, datetime, `classdef` OOP, community plugin host
(`openmatlab plugins`), Desktop-style workbench (`openmatlab workbench`). Language is a
**matrix+procedural MVP**, not full MATLAB.
See `docs/ARCHITECTURE.md` and `docs/acceptance/`. Where this paragraph names a file under `docs/milestones/`, that file is the written acceptance for the date it records. Historical corpus figures, C-MAPSS, and the control sample are scoped in [What these records mean](#what-these-records-mean).

```bash
pip install -e ".[dev]"
openmatlab status                 # five-layer QA blurb
openmatlab features               # layer 1: capability map
openmatlab cases                  # layer 2: use/test cases
openmatlab defects                # layer 5: GitHub Issues via gh
openmatlab test --suite unit      # layer 3+4: pytest
pytest -m "unit or bdd" --cov=openmatlab
```

Agents: `AGENTS.md` · Readiness: `docs/READY.md` · Process: `docs/PROCESS.md` · `CONTRIBUTING.md`  
QA: `docs/QA.md` · Issues = work · Gherkin `features/` · `docs/feature_map.yaml` (sync) · CI `.github/workflows/ci.yml`

Desktop builds and signing setup: [Desktop releases](docs/DESKTOP-RELEASES.md).

### Non-goals

- **No reverse engineering** of proprietary MATLAB binaries / internals
- No RE tools (IDA, Ghidra, Hopper, …) against MATLAB
- Not a drop-in MathWorks MATLAB replacement
- Simulink-class environments: non-goal / far future

### What these records mean

[中文](#这些记录指什么). Two layers stay separate: one historical corpus run, and what this tree's files say.

#### Historical corpus run

[`docs/corpus/REPORT.md`](docs/corpus/REPORT.md#pass-rate-by-tier) is generated from [`docs/corpus/results.json`](docs/corpus/results.json). That JSON records:

- `commit` `5d9513a4974fde8fa54340fcf11c21b57defcc11`. The report line prints the first 12 hex digits, `5d9513a4974f`, because `render` in `src/openmatlab/qa/corpus/report.py` keeps only that prefix.
- `generated` `2026-10-23T03:19:42Z`, which is 2026-10-23 11:19:42 in Asia/Shanghai (UTC+8). That clock is what `results.save` in `src/openmatlab/qa/corpus/results.py` stores. It is not the committer time of the recorded commit. Commit `5d9513a4974fde8fa54340fcf11c21b57defcc11` has committer time `2026-10-22T20:16:27-07:00` (2026-10-23 11:16:27 Asia/Shanghai).
- The last commit that changes `docs/corpus/REPORT.md` is `8fd7d93c8853a852db1bf92520868deabb11a8f7`, committer time `2026-10-22T20:35:45-07:00` (2026-10-23 11:35:45 Asia/Shanghai).
- `full_run` true. The corpus CLI writes true when `--sample` is omitted or `0` (`full_run=not a.sample` in `src/openmatlab/qa/corpus/__main__.py`), which keeps every manifest entry instead of every Nth entry. The JSON does not store a stride.
- `timeout` `20.0`. The report prints `timeout 20.0 s`. That field is the budget stored on this JSON. It is not the later per-entry floor in `src/openmatlab/qa/corpus/pipeline.py`.

The file holds 6130 records: octave 5036, rosetta 649, chebfun 326, matlab2tikz 119.

Tier rates use `tier_outcome` in `src/openmatlab/qa/corpus/report.py`. A record is outside the denominator when `excluded` drops it, and also when that tier's field is not `pass`, `error`, `timeout`, or `crash`. For every tier, `excluded` drops `corpus-noise` (123 records: rosetta 122, matlab2tikz 1). For T1–T3 it also drops `toolbox:*` (874) and `io-env` (54). The 874 `toolbox:*` records are the category rows in that report (442 + 380 + 38 + 12 + 2).

| Tier | Rate on that run | Counted | `corpus-noise` | `toolbox:*` | `io-env` | Tier field outside `pass`/`error`/`timeout`/`crash` |
|---|---|---|---|---|---|---|
| T0 | 99.5 % (966/971) | 971 | 123 | 0 | 0 | 5036 |
| T1 | 70.5 % (474/672) | 672 | 123 | 874 | 54 | 4407 |
| T2 | 82.8 % (3442/4159) | 4159 | 123 | 874 | 54 | 920 |
| T3 | 75.3 % (55/73) | 73 | 123 | 874 | 54 | 5006 |

Each row sums to 6130. The T0 remainder 5036 is every Octave record: each has `t0` `n/a`. Category `pass` is 3896 of the 6130 records. That tally is not a tier rate.

The four sources are the pinned corpus in that JSON (Rosetta Code, GNU Octave, chebfun, matlab2tikz). These rates are not a share of arbitrary MATLAB projects. This historical run is not a full-corpus result for a later `main` commit. This README does not report a new full run.

The report's own run line is:

```text
Run: commit `5d9513a4974f`, generated 2026-10-23T03:19:42Z, full run: yes, timeout 20.0 s.
```

#### This tree

[M3 written acceptance (2026-10-16)](docs/milestones/M3-domain-toolboxes.md#close-out-2026-10-16) records 7/7 written criteria. T03 in that file's criteria table is the written `ode45` / `ode23` slice. The residual table in that file names <https://github.com/superche/openmatlab/issues/657> (ODE Events/Mass/stiff, deval, Waypoints, Display).

In this tree, `ode45` and `ode23` are both `_solver` in `src/openmatlab/libs/odeopt.py`. They apply `RelTol`, `AbsTol`, `Refine`, `MaxStep`, and `InitialStep` (`_APPLIED_OPTIONS`). `_reject_unimplemented_options` raises `OpenMATLAB:ode45:UnsupportedOption` or `OpenMATLAB:ode23:UnsupportedOption` for another nonempty option, including `Events` and `Mass`, before `f(t, y)`. The text `off` is accepted only for `BDF`, `JConstant`, `NormControl`, `Stats`, and `Vectorized`.

[M12 written acceptance (2026-10-23)](docs/milestones/M12-corpus-gate.md#close-out-2026-10-23) records written criteria 10/10. The percentages in the table above are that historical run. The progress snapshot in the same milestone file also quotes earlier runs. Those earlier percentages are not this JSON.

[C-MAPSS](demos/cmapss/README.md#what-this-demo-is) analyzes the published FD001 tables. [M14 intent](docs/milestones/M14-cmapss-vertical.md#intent) is that story: download, read, preprocess, metrics, and a figure. The demo does not simulate an engine.

[Control examples](demos/plugins/README.md#control-examples-in-this-directory) register `tf` and `step` as functions that return strings. That sample is an architectural stub, not a computational control toolbox.

### Roadmap

In this list, **done** means the written close-out recorded in the milestone file.

1. Architecture seams — **done**
2. Array Value + NumPy backend — **done** (Epic #1)
3. Matrix language + evaluator + display — **done** (Epic #1)
4. Plot MVP — **done** (Epic #1); interactive policy — **done** (Epic #2)
5. Functions / path / scripts / control flow / cells — **done** (Workbench MVP + M2 exit)
6. Plugin host, domain conformance gate, MATLAB-aligned Workbench — **done** (M4–M6)
7. MATLAB core language & I/O — **done** (M7); M3 — written close-out recorded (not a complete control toolbox); Object system — **done** (M8); Tables (M10) and Debugger (M11) — **done**; corpus gate (M12) and graphics (M13) — **done** (close-out 2026-10-23); vertical close-outs C-MAPSS (M14), MIT-BIH (M15), BBBC038 (M16) — written close-outs recorded
8. Analyst pipeline (M17) — story `demos/analyst`, criteria `docs/milestones/M17-analyst-pipeline.md` (does not clear the Core backlog; milestone stays open)
9. Simulink-class — *out of scope near-term*

### License

MIT © Shaw Che / superche, 2026

---

## 中文

**OpenMATLAB** 是洁净室开源的 **矩阵优先** MATLAB 兼容工作台：基于公开规范，
**不**逆向专有 MATLAB 二进制。

### 状态（v0.0.2+ — 后 MVP 工作台）

里程碑书面验收（2026-10-31 对照 GitHub）：M1 Workbench MVP、M2 Octave-breadth（19/19 准则）、M3 书面准则（7/7，2026-10-16 close-out）、M4 插件宿主、M5 领域业务一致性、M6 MATLAB 对齐工作台、M7 MATLAB 核心语言与 I/O（11/11 准则，2026-10-13 关闭）、M8 对象系统（10/10 准则，2026-10-16 关闭）、M10 表格与数据类型（10/10）、M11 调试器与工作台（10/10，均 2026-10-16 关闭）、M12 真实脚本兼容性门禁（10/10，2026-10-23 关闭）、M13 图形补全（10/10，2026-10-23 关闭）、M14 C-MAPSS（10/10，2026-10-23 关闭）、M15 MIT-BIH（10/10，2026-10-23 关闭）、M16 BBBC038（10/10，2026-10-25 关闭）。开放：核心待办（milestone/9，p2 残留，见 `docs/GAP-ANALYSIS.md`）与 M17 分析师流水线（milestone/17，未关闭；缺失值 × CSV 导入切片 × groupsummary 故事 × `demos/analyst`；准则 `docs/milestones/M17-analyst-pipeline.md`）。垂线演示：`demos/cmapss`、`demos/mitbih`、`demos/bbbc038`。已可用：矩阵 REPL、NumPy、控制流、脚本与 `.m` 函数、cell、`addpath`/`which`、句柄图形（figure/axes/get/set、hold、subplot、saveas）、try/catch、varargin、文件 I/O 与 save/load、containers.Map、datetime、`classdef` OOP、社区插件宿主、`openmatlab workbench`。语言仍是 **矩阵+过程式 MVP**，不是完整 MATLAB。详见 `docs/ARCHITECTURE.md` 与 `docs/acceptance/`。本段写明 `docs/milestones/` 路径时，该文件就是所记日期上的书面验收。历史语料数字、C-MAPSS 与控制示例的范围见 [这些记录指什么](#这些记录指什么)。

### 这些记录指什么

[English](#what-these-records-mean)。两层分开：一次历史语料运行，以及本树里的文件写了什么。

#### 历史语料运行

[`docs/corpus/REPORT.md`](docs/corpus/REPORT.md#pass-rate-by-tier) 由 [`docs/corpus/results.json`](docs/corpus/results.json) 生成。该 JSON 记录：

- `commit` 为 `5d9513a4974fde8fa54340fcf11c21b57defcc11`。报告正文只印前 12 位十六进制 `5d9513a4974f`，因为 `src/openmatlab/qa/corpus/report.py` 的 `render` 只保留这个前缀。
- `generated` 为 `2026-10-23T03:19:42Z`，即 Asia/Shanghai（UTC+8）2026-10-23 11:19:42。这是 `src/openmatlab/qa/corpus/results.py` 里 `results.save` 写入的时钟，不是所记提交的 committer 时间。提交 `5d9513a4974fde8fa54340fcf11c21b57defcc11` 的 committer 时间是 `2026-10-22T20:16:27-07:00`（Asia/Shanghai 2026-10-23 11:16:27）。
- 最后一次修改 `docs/corpus/REPORT.md` 的提交是 `8fd7d93c8853a852db1bf92520868deabb11a8f7`，committer 时间 `2026-10-22T20:35:45-07:00`（Asia/Shanghai 2026-10-23 11:35:45）。
- `full_run` 为 true。语料命令行在 `--sample` 省略或为 `0` 时把该字段写成 true（`src/openmatlab/qa/corpus/__main__.py` 中 `full_run=not a.sample`），也就是保留清单中的每一条，而不是每隔 N 条取一条。JSON 没有另存步长。
- `timeout` 为 `20.0`。报告印出 `timeout 20.0 s`。该字段是这份 JSON 保存的预算，不是 `src/openmatlab/qa/corpus/pipeline.py` 里后来的按条目下限。

文件中有 6130 条记录：octave 5036，rosetta 649，chebfun 326，matlab2tikz 119。

分层比率使用 `src/openmatlab/qa/corpus/report.py` 的 `tier_outcome`。记录在两种情况下不进入分母：`excluded` 将其去掉，或该层字段不是 `pass`、`error`、`timeout`、`crash`。每一层里，`excluded` 都去掉 `corpus-noise`（123 条：rosetta 122，matlab2tikz 1）。T1–T3 还去掉 `toolbox:*`（874）和 `io-env`（54）。这 874 条 `toolbox:*` 就是该报告类别表中的各行（442 + 380 + 38 + 12 + 2）。

| 层 | 该次运行的比率 | 计入 | `corpus-noise` | `toolbox:*` | `io-env` | 层字段不属于 `pass`/`error`/`timeout`/`crash` |
|---|---|---|---|---|---|---|
| T0 | 99.5 % (966/971) | 971 | 123 | 0 | 0 | 5036 |
| T1 | 70.5 % (474/672) | 672 | 123 | 874 | 54 | 4407 |
| T2 | 82.8 % (3442/4159) | 4159 | 123 | 874 | 54 | 920 |
| T3 | 75.3 % (55/73) | 73 | 123 | 874 | 54 | 5006 |

每一行加总为 6130。T0 的余数 5036 是全部 Octave 记录：每条的 `t0` 都是 `n/a`。类别 `pass` 是 6130 条中的 3896 条。这个计数不是某一层的比率。

这四个来源是该 JSON 中钉住的语料（Rosetta Code、GNU Octave、chebfun、matlab2tikz）。这些比率不是任意 MATLAB 工程能跑通的比例。这次历史运行不是此后某个 `main` 提交上的新全量语料结果。本 README 不报告新的全量运行。

报告自己的运行行是：

```text
Run: commit `5d9513a4974f`, generated 2026-10-23T03:19:42Z, full run: yes, timeout 20.0 s.
```

#### 本树

[M3 书面验收（2026-10-16）](docs/milestones/M3-domain-toolboxes.md#close-out-2026-10-16) 记录书面准则 7/7。该文件准则表中的 T03 是所写的 `ode45` / `ode23` 切片。该文件的残留表写有 <https://github.com/superche/openmatlab/issues/657>（ODE Events/Mass/stiff、deval、Waypoints、Display）。

在本树中，`ode45` 与 `ode23` 都是 `src/openmatlab/libs/odeopt.py` 里的 `_solver`。它们应用 `RelTol`、`AbsTol`、`Refine`、`MaxStep` 与 `InitialStep`（`_APPLIED_OPTIONS`）。`_reject_unimplemented_options` 在调用 `f(t, y)` 之前，对另一个非空选项（包括 `Events` 与 `Mass`）抛出 `OpenMATLAB:ode45:UnsupportedOption` 或 `OpenMATLAB:ode23:UnsupportedOption`。文本 `off` 只适用于 `BDF`、`JConstant`、`NormControl`、`Stats` 与 `Vectorized`。

[M12 书面验收（2026-10-23）](docs/milestones/M12-corpus-gate.md#close-out-2026-10-23) 记录书面准则 10/10。上表百分比属于那次历史运行。同一里程碑文件的进度叙述还引用更早的运行。那些更早的百分比不是这份 JSON。

[C-MAPSS](demos/cmapss/README.md#what-this-demo-is) 分析已发表的 FD001 表。[M14 的 Intent](docs/milestones/M14-cmapss-vertical.md#intent) 是这条故事：下载、读取、预处理、指标和一幅图。该演示不仿真发动机。

[控制示例](demos/plugins/README.md#control-examples-in-this-directory) 把 `tf` 与 `step` 注册为返回字符串的函数。该示例是架构桩，不是可计算的控制工具箱。

状态列表里的 **done** 与「书面 close-out」同义：只表示里程碑文件里记录的书面验收。

### 明确非目标

- 不逆向 MATLAB；不使用逆向工具分析 MATLAB
- 不是 MathWorks 产品的即插即用替代
- Simulink 类：近期非目标

### 许可证

MIT © Shaw Che / superche, 2026
