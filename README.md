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

1. **Parser** — MATLAB-like syntax from public language docs — **done (minimal subset)**
2. **Runtime** — interpreter / execution model — **done (scalar env + eval)**
3. **Core math** — arrays, linear algebra, common numeric APIs — *next*
4. **Plotting** — basic visualization layer — *planned*

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

1. **解析器** — 基于公开语言文档 — **已完成（最小子集）**
2. **运行时** — 解释器 / 执行模型 — **已完成（标量环境）**
3. **核心数学** — 数组、线性代数 — *下一步*
4. **绘图** — 基础可视化 — *计划中*

### 许可证

MIT © Shaw Che / superche, 2026
