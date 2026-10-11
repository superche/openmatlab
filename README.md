# OpenMATLAB / 开源 MATLAB 兼容实现

**English** | [中文](#中文)

## English

**OpenMATLAB** is a clean-room, open-source MATLAB-compatible **matrix-first
workbench** (language + runtime + libs), built from **public specs** — not from
proprietary MATLAB binaries.

### Status (v0.0.2 — architecture stage)

Package seams and interfaces are in place (`host`, `lang`, `runtime`,
`numerics`, `graphics`, `libs`). **Evaluation is not wired yet** (by design).
See `docs/ARCHITECTURE.md`.

```bash
pip install -e ".[dev]"
openmatlab --status
python -m openmatlab --version
pytest
```

### Non-goals

- **No reverse engineering** of proprietary MATLAB binaries / internals
- No RE tools (IDA, Ghidra, Hopper, …) against MATLAB
- Not a drop-in MathWorks MATLAB replacement
- Simulink-class environments: non-goal / far future

### Roadmap

1. Architecture seams — **done (this stage)**
2. Array Value + NumPy backend — *next*
3. Matrix language (lexer/parser) + evaluator + display policy
4. Plot MVP
5. Functions / path / toolboxes
6. Simulink-class — *out of scope near-term*

### License

MIT © Shaw Che / superche, 2026

---

## 中文

**OpenMATLAB** 是洁净室开源的 **矩阵优先** MATLAB 兼容工作台：基于公开规范，
**不**逆向专有 MATLAB 二进制。

### 状态（v0.0.2 — 架构阶段）

已搭好包边界与接口；**求值尚未接通**（刻意为之）。详见 `docs/ARCHITECTURE.md`。

### 明确非目标

- 不逆向 MATLAB；不使用逆向工具分析 MATLAB
- 不是 MathWorks 产品的即插即用替代
- Simulink 类：近期非目标

### 许可证

MIT © Shaw Che / superche, 2026
