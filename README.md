# OpenMATLAB / 开源 MATLAB 兼容实现

**English** | [中文](#中文)

## English

**OpenMATLAB** is a clean-room, open-source reimplementation of a MATLAB-compatible language, runtime, and core libraries, built from **public language documentation and specifications**—not from proprietary MATLAB binaries.

### Purpose

- Provide an open MATLAB-compatible language, interpreter/runtime, and libraries
- Base the design on publicly available language docs and Octave-compatible ideas
- Enable research, education, and interoperable tooling without proprietary lock-in

### Non-goals (explicit)

- **No reverse engineering** of proprietary MATLAB binaries, object code, or internals
- No use of reverse-engineering tools (e.g. IDA, Ghidra, Hopper) against MATLAB
- Not a drop-in replacement for MathWorks MATLAB products

### Current status (v0.0.1)

**Done / in progress — scalar expression subset:**

- Lexer + parser: numbers, identifiers, `+ - * /`, parentheses, `a = expr`, `;` / newlines, `%` comments
- AST evaluator with variable environment (scalars)
- CLI / REPL: `openmatlab`, `python -m openmatlab`, `-e CODE`, script files

```bash
pip install -e ".[dev]"
openmatlab -e "a = 1 + 2 * 3; a"
python -m openmatlab   # REPL
pytest
```

### Roadmap

See `docs/ARCHITECTURE.md` for the calibrated (matrix-first workbench) plan.

1. **Parser** — MATLAB-like syntax from public language docs — **scalar subset done**; matrix/index/colon/`.*` next
2. **Runtime** — Array-first values + workspace — **scalar prototype only** (not product-ready)
3. **Core math** — arrays, linear algebra (NumPy-backed OK) — *next after Value/Array*
4. **Host display + plotting** — `;` suppress, pretty-print, `plot` MVP — *MVP-critical*
5. **Functions / path / toolboxes** — *later*
6. **Simulink-class** — *non-goal / far future*

### License

MIT © Shaw Che / superche, 2026

---

## 中文

**OpenMATLAB** 是一个洁净室（clean-room）开源项目：基于**公开语言文档与规范**，实现 MATLAB 兼容的语言、运行时与核心库——**不**对专有 MATLAB 二进制进行逆向工程。

### 目标

- 提供开源的 MATLAB 兼容语言、解释器/运行时与库
- 以公开文档及 Octave 兼容思路为设计依据
- 支持研究、教学与可互操作工具链

### 明确非目标

- **不**对专有 MATLAB 二进制、目标码或内部实现做逆向工程
- 不使用逆向工具分析 MATLAB
- 不是 MathWorks MATLAB 产品的官方替代品

### 当前状态（v0.0.1）

**已完成 / 进行中 — 标量表达式子集：**

- 词法/语法：数字、标识符、四则运算、括号、赋值、`;`/换行、`%` 注释
- AST 求值与变量环境（标量）
- CLI / REPL：`openmatlab`、`python -m openmatlab`、`-e`、脚本文件

### 路线图

详细标定架构见 `docs/ARCHITECTURE.md`（矩阵优先工作台）。

1. **解析器** — 公开语言文档 — **标量子集已完成**；矩阵/下标/冒号/`.*` 下一步
2. **运行时** — Array-first 值 + 工作区 — **仅标量原型**（未达产品 MVP）
3. **核心数学** — 数组、线性代数（可用 NumPy 后端）— *在 Value/Array 之后*
4. **交互显示 + 绘图** — `;` 抑制输出、矩阵打印、`plot` MVP — *MVP 关键*
5. **函数 / 路径 / 工具箱** — *稍后*
6. **Simulink 类** — *非目标 / 远期*

### 许可证

MIT © Shaw Che / superche, 2026
