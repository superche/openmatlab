# OpenMATLAB / 开源 MATLAB 兼容实现

**English** | [中文](#中文)

## English

**OpenMATLAB** is a clean-room, open-source MATLAB-compatible **matrix-first
workbench** (language + runtime + libs), built from **public specs** — not from
proprietary MATLAB binaries.

### Status (v0.0.2+ — post-MVP workbench)

Closed milestones (GitHub, checked 2026-10-31): Workbench MVP (M1), Octave-breadth (M2, 19/19 criteria), Domain toolboxes (M3, 7/7 criteria,
closed 2026-10-16; `docs/milestones/M3-domain-toolboxes.md`), Plugin host (M4), Domain business-conformance (M5),
MATLAB-aligned Workbench (M6), MATLAB core language & I/O (M7, 11/11 criteria, closed 2026-10-13;
`docs/milestones/M7-core-language-io.md`), Object system (M8, 10/10 criteria, closed 2026-10-16;
`docs/milestones/M8-object-system.md`), Tables and data types (M10, 10/10, closed 2026-10-16; `docs/milestones/M10-tables.md`), Debugger and Workbench (M11, 10/10, closed 2026-10-16; `docs/milestones/M11-debugger-workbench.md`), Real-script compatibility gate (M12, 10/10, closed 2026-10-23; `docs/milestones/M12-corpus-gate.md`), Graphics completion (M13, 10/10, closed 2026-10-23; `docs/milestones/M13-graphics.md`), C-MAPSS PHM vertical (M14, 10/10, closed 2026-10-23; `docs/milestones/M14-cmapss-vertical.md`), MIT-BIH Arrhythmia vertical (M15, 10/10, closed 2026-10-23; `docs/milestones/M15-mitbih-vertical.md`), BBBC038 nuclei image vertical (M16, 10/10, closed 2026-10-25; `docs/milestones/M16-bbbc038-vertical.md`). Open: Core backlog (milestone/9, p2 residuals; `docs/GAP-ANALYSIS.md`) and M17 Analyst pipeline (milestone/17, open; missing values × CSV import slice × groupsummary story cut × `demos/analyst`; criteria `docs/milestones/M17-analyst-pipeline.md`). Vertical demos: `demos/cmapss`, `demos/mitbih`, `demos/bbbc038`. Works today: matrix REPL (`-e` / bare), NumPy arrays, control
flow, scripts and `.m` functions, cells, `addpath`/`which`, handle graphics (figure/axes/get/set, hold, subplot, saveas), try/catch, varargin, file I/O and save/load, containers.Map, datetime, `classdef` OOP, community plugin host
(`openmatlab plugins`), Desktop-style workbench (`openmatlab workbench`). Language is a
**matrix+procedural MVP**, not full MATLAB.
See `docs/ARCHITECTURE.md` and `docs/acceptance/`.

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

### Roadmap

1. Architecture seams — **done**
2. Array Value + NumPy backend — **done** (Epic #1)
3. Matrix language + evaluator + display — **done** (Epic #1)
4. Plot MVP — **done** (Epic #1); interactive policy — **done** (Epic #2)
5. Functions / path / scripts / control flow / cells — **done** (Workbench MVP + M2 exit)
6. Plugin host, domain conformance gate, MATLAB-aligned Workbench — **done** (M4–M6)
7. MATLAB core language & I/O — **done** (M7); Domain toolboxes — **done** (M3); Object system — **done** (M8); Tables (M10) and Debugger (M11) — **done**; corpus gate (M12) and graphics (M13) — **done** (closed 2026-10-23); verticals C-MAPSS (M14), MIT-BIH (M15), BBBC038 (M16) — **done**
8. Analyst pipeline (M17) — story `demos/analyst`, criteria `docs/milestones/M17-analyst-pipeline.md` (does not clear the Core backlog; milestone stays open)
9. Simulink-class — *out of scope near-term*

### License

MIT © Shaw Che / superche, 2026

---

## 中文

**OpenMATLAB** 是洁净室开源的 **矩阵优先** MATLAB 兼容工作台：基于公开规范，
**不**逆向专有 MATLAB 二进制。

### 状态（v0.0.2+ — 后 MVP 工作台）

已关闭里程碑（2026-10-31 对照 GitHub）：M1 Workbench MVP、M2 Octave-breadth（19/19 准则）、M3 领域工具箱（7/7 准则，2026-10-16 关闭）、M4 插件宿主、M5 领域业务一致性、M6 MATLAB 对齐工作台、M7 MATLAB 核心语言与 I/O（11/11 准则，2026-10-13 关闭）、M8 对象系统（10/10 准则，2026-10-16 关闭）、M10 表格与数据类型（10/10）、M11 调试器与工作台（10/10，均 2026-10-16 关闭）、M12 真实脚本兼容性门禁（10/10，2026-10-23 关闭）、M13 图形补全（10/10，2026-10-23 关闭）、M14 C-MAPSS（10/10，2026-10-23 关闭）、M15 MIT-BIH（10/10，2026-10-23 关闭）、M16 BBBC038（10/10，2026-10-25 关闭）。开放：核心待办（milestone/9，p2 残留，见 `docs/GAP-ANALYSIS.md`）与 M17 分析师流水线（milestone/17，未关闭；缺失值 × CSV 导入切片 × groupsummary 故事 × `demos/analyst`；准则 `docs/milestones/M17-analyst-pipeline.md`）。垂线演示：`demos/cmapss`、`demos/mitbih`、`demos/bbbc038`。已可用：矩阵 REPL、NumPy、控制流、脚本与 `.m` 函数、cell、`addpath`/`which`、句柄图形（figure/axes/get/set、hold、subplot、saveas）、try/catch、varargin、文件 I/O 与 save/load、containers.Map、datetime、`classdef` OOP、社区插件宿主、`openmatlab workbench`。语言仍是 **矩阵+过程式 MVP**，不是完整 MATLAB。详见 `docs/ARCHITECTURE.md` 与 `docs/acceptance/`。

### 明确非目标

- 不逆向 MATLAB；不使用逆向工具分析 MATLAB
- 不是 MathWorks 产品的即插即用替代
- Simulink 类：近期非目标

### 许可证

MIT © Shaw Che / superche, 2026
