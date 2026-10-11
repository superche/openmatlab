# OpenMATLAB / 开源 MATLAB 兼容实现

**English** | [中文](#中文)

## English

**OpenMATLAB** is a clean-room, open-source MATLAB-compatible **matrix-first
workbench** (language + runtime + libs), built from **public specs** — not from
proprietary MATLAB binaries.

### Status (v0.0.2+ — post-MVP workbench)

Epics [#1](https://github.com/superche/openmatlab/issues/1) and [#19](https://github.com/superche/openmatlab/issues/19) are closed:
matrix REPL (`-e` / bare), NumPy arrays, control flow, `.m` functions, `addpath`/`which`,
plot MVP, CI on `main`. Language is still a **matrix+control MVP**, not full MATLAB.
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
5. Functions / path / toolboxes — **MVP done**; deepen next
6. Language residuals (`while`/`break`, scripts, single-quoted chars) — *candidate Epic #3*
7. Simulink-class — *out of scope near-term*

### License

MIT © Shaw Che / superche, 2026

---

## 中文

**OpenMATLAB** 是洁净室开源的 **矩阵优先** MATLAB 兼容工作台：基于公开规范，
**不**逆向专有 MATLAB 二进制。

### 状态（v0.0.2+ — 后 MVP 工作台）

Epic [#1](https://github.com/superche/openmatlab/issues/1) 与 [#19](https://github.com/superche/openmatlab/issues/19) 已关闭：矩阵 REPL、NumPy、控制流、`.m` 函数、`addpath`/`which`、plot MVP、`main` CI 已通。语言仍是 **矩阵+控制 MVP**，不是完整 MATLAB。详见 `docs/ARCHITECTURE.md` 与 `docs/acceptance/`。

### 明确非目标

- 不逆向 MATLAB；不使用逆向工具分析 MATLAB
- 不是 MathWorks 产品的即插即用替代
- Simulink 类：近期非目标

### 许可证

MIT © Shaw Che / superche, 2026
