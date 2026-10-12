# OpenMATLAB 复盘：洁净室产品、可度量出口与拒绝假完成

> 面向 Tech Leads / CTOs 的分享稿。仓库：[superche/openmatlab](https://github.com/superche/openmatlab)。  
> 本文强调**业务判断与工程纪律**，不是工具清单。

---

## 0. 两句话结论

OpenMATLAB 从「软件工程式上盘」收敛为**矩阵优先、公开规格、洁净室**的 MATLAB 兼容工作台：架构按 seams 切开，交付按里程碑与 Epic 验收证据推进，CI 门禁与 GitHub Issues 作为唯一事实源。对 CTO 真正有用的不是「又多写了多少功能」，而是学会区分**加载成功 ≠ 语义正确**、**桌面壳 ≠ 领域正确**、**社区契约 ≠ 专有工具箱**，以及何时用可度量出口标准叫停「进度剧场」。

---

## 1. 弧线：从 SWE 上盘到可验收产品

### 1.1 起点：上盘容易，产品意图难

早期很容易把 OpenMATLAB 做成「又一个通用 IDE / 又一套脚本解释器」。那条路技术上热闹，业务上失焦。我们很快把产品意图钉死：

- **矩阵优先**的科学工作台：试算 → 显示 → 绘图 → 再接领域库；
- **洁净室 / 公开规格**：不逆向 MATLAB 二进制，不依赖专有运行时；
- **非目标写进 README**：不是 MathWorks 即插即用替代，Simulink 类近期末做。

意图一清晰，架构、里程碑和「何时算完成」才有意义。

### 1.2 洁净室架构：先 seams，再功能

包边界按职责切开，而不是按「MATLAB 有什么菜单」堆文件：

| Seam | 职责 |
|------|------|
| `host` | CLI / REPL / Desktop / Workbench 壳 |
| `lang` | 词法 / AST / 解析（矩阵语法是一等公民） |
| `runtime` | `Value`/`Array`、Workspace、Evaluator、Session |
| `numerics` | `ArrayBackend`（NumPy 实现） |
| `graphics` | `GraphicsBackend`（Matplotlib，默认 Agg） |
| `libs` | 路径 / 数值 builtins / 工具箱入口 |
| `extensions` | VS Code 风格插件宿主 |
| `qa` | feature map / catalog / Issues 桥 |

跨包只依赖稳定 Protocol。Session 是组合根。这让后续换后端、加插件、做桌面壳时，不必拆散语言内核。

### 1.3 QA 与流程：把「做完」定义成可审计事件

五层 QA（Issues → cases/Gherkin → 环境 → pytest/CLI → 缺陷）配上强制门禁：

- PR 合并靠 CI 检查名 **`test`**；
- Epic 关闭必须有 `docs/acceptance/EPIC-NNN.md`（真实命令输出，禁止编造）；
- 双 tip：功能 tip（验收代码落地）+ 证据 tip（验收文档合入 `main`）；
- residual 必须落成 GitHub Issues，文档不能替代工单。

公开仓库、Actions CI、受保护的 `main`，把「本地看起来能跑」升级为「社区可复验」。

### 1.4 里程碑弧：从语言广度到宿主产品

| 阶段 | 意图 | 业务含义 |
|------|------|----------|
| M1 Workbench MVP | REPL、脚本、控制流、plot MVP | 证明「能用」的最小闭环 |
| M2 Octave-breadth | 语言 + 数值核心向公开语义靠拢 | **可度量出口**（conformance 11/11） |
| M4 Plugin host | 社区插件契约与宿主 | 领域能力外置，不把壳做死 |
| M5 Domain conformance | 参考向量门禁（如 window APIs） | 加载成功之后，还要语义诚实 |
| M6 Workbench-aligned | MATLAB Desktop 式 Host chrome | 产品形态，而非 notebook 薄壳 |
| M3 Domain toolboxes | 更重领域库（社区插件之上） | 契约与门禁之后再扩张 |

弧线不是「功能堆叠」，而是**意图 → seams → 可验收广度 → 宿主契约 → 领域诚实 → 产品壳**。

---

## 2. 技术选择：为什么这样切，而不是那样炫

### 2.1 Array-first，而不是「标量语言 + 矩阵库」

MATLAB 语义里，标量就是 1×1 数组。把 `float` 环境当一等公民，再补矩阵，会在索引、广播、显示和 builtins 上持续出血。我们选择：

- `Value` / `Array` 协议 + `NDArrayValue`；
- 标量即 1×1；
- `*` 与 `.*` 在词法与求值层分离。

这是第一性原理：产品是矩阵工作台，运行时就该是矩阵优先。

### 2.2 五条 seams：换后端不换世界观

Host / lang / runtime / numerics / graphics 切开，带来三件 CTO 关心的事：

1. **可替换**：NumPy、Matplotlib 是实现，不是身份；
2. **可测试**：语言与图形、CLI 与内核可分层测；
3. **可扩展**：插件与桌面挂在 Host/API 上，不侵入 Evaluator。

「架构友好」不是口号，而是每次迭代仍能穿过 seams 落地的约束。

### 2.3 插件：C + B + A，而不是「再 fork 一个 Desktop」

插件方案对标 VS Code，锁定组合：

- **C（骨干）**：Host 拥有 slots（commands / panels / menus / …），插件只填槽；
- **B（默认发现）**：`plugin.yaml` + load path（贴近 toolbox / `addpath` 心智）；
- **A（可选分发）**：`importlib.metadata` entry points（pip/wheel 生态）。

微前端（Option D）明确推迟。原则只有一句：**插件永不 fork 壳**。社区插件契约成立，领域扩张才不会变成「每个工具箱一份 Desktop」。

### 2.4 不做的事，和故意选的后端

- **不做**：逆向 MATLAB、依赖专有运行时、宣称 bit-for-bit / 全工具箱对等；
- **做**：公开文档语义 + Octave 风格广度参考；
- **后端**：NumPy（数组）与 Matplotlib（绘图）——成熟、可审计、可替换。

洁净室不是法律免责声明 alone，它是架构过滤器：进不了公开规格的东西，就不进核心。

---

## 3. 协作系统：原则、对抗式审查与可复验证据

### 3.1 AGENTS.md：短原则，长流程另册

协作原则压成可执行的几条（细节在 `PROCESS.md` / `QA.md`）：

| 原则 | 落地含义 |
|------|----------|
| 第一性原理 | 抽象错了就停，不在错误模型上打补丁 |
| KISS | 先让接口对，再优化 |
| LSP | 实现 `Value`/`Array`/`ArrayBackend` 时不破坏调用方假设 |
| Occam / Deslop | 同等效果选更简单设计与更小 diff；删噪声优于耍聪明 |
| 测试服务需求 | 禁止为变绿而削弱用例；需求变则同步改 map/catalog/Gherkin |

对抗式自审对照这些原则，而不是对照「我这周提交了多少行」。

### 3.2 Epic 有序验收：优先级驱动，而不是顺手驱动

选下一个 Epic 的规则很硬：取当前里程碑文档里**最高优先级未满足准则**（p0 > p1，再按表序），不是「顺手能做的」。

M2 用 conformance manifest + **strict xfail**：脚本未过则 xfail；一旦实现让它通过，manifest 未标 `met` 时 CI 失败。进度无法「口头超前」。

### 3.3 双 tip 与 EPIC-NNN：完成必须可复跑

每个 Epic Done 至少包含：

- 关联 Issues / PRs；
- **功能 tip SHA** 与 **证据合并 tip SHA**；
- CI check **`test`** 链接；
- pytest markers 结果、feature_map 状态、CLI/烟雾演示；
- Milestone progress：criteria met/total、剩余 gap。

Showcase 录像在需要时补（插件宿主、Workbench chrome）：文字验收证明「对」，录像证明「像产品」。

### 3.4 GitHub Issues = 唯一待办系统

禁止：agent 本地 todo、聊天清单、文档内未落 Issue 的待办。文档只链接与汇总。Milestones（M1–M6）承载路线图；`feature_map.yaml` 是同步清单，不是第二套工单库。

这对多智能体 / 多人并行尤其关键：**事实源唯一，残留才不会蒸发**。

---

## 4. 业务智慧：何时停、何时诚实、何时扩张

### 4.1 何时停止：M2 出口 vs 假完成

M2 在 **11/11 criteria met、0 open p0** 时，出口标准已满足。我们仍可选择**保持里程碑 OPEN**，继续消化 p1/p2 广度——但那是**显式决策**，不是把「还在做」伪装成「还没到出口」。

假完成的典型形态：

- feature_map 提前标 `done`，notes 却写不清缺口；
- CI 绿但用例被削薄；
- Epic 关了，residual 只写在散文里。

可度量出口标准的价值，是给管理层一个**叫停或转向的把手**。

### 4.2 加载 ≠ 正确性

插件能 `activate`、路径能 `which`、函数能调用，只说明**宿主通路通了**。领域里程碑（M5）用参考向量（如 `hamming` / `rectwin` / `blackman`）做业务一致性门禁：同一套「strict xfail → met」诚实模型。

CTO 问法应是：*「这条领域 API 在公开语义下，参考向量过了吗？」* 而不是 *「插件列表里有没有这个名字？」*

### 4.3 桌面 ≠ 领域

Workbench（M6）交付的是 **Host 拥有的 chrome 与布局**（命令窗、编辑器、工作区、当前文件夹、图形、菜单/工具条/停靠）。它提升的是产品可用性与插件槽位体验，**不证明**信号处理或控制库正确。

把「看起来像 MATLAB Desktop」当成「领域完成」，是经典的进度剧场。我们刻意拆开：面板 MVP → 布局对等 →（另线）领域门禁与工具箱。

### 4.4 社区契约 vs 专有工具箱

插件宿主的明确非目标：移植或包装 MathWorks 专有工具箱。开放的是**社区合同**——manifest、slots、Host API、版本区间、故障隔离。

业务含义：生态增长靠可预期的扩展点与许可证清晰的社区实现，而不是灰色兼容层。契约先于广度，门禁先于「Domain toolboxes」扩张。

### 4.5 进度剧场 vs 可度量出口

| 剧场信号 | 可度量替代 |
|----------|------------|
| 「架构已经完成」 | seams + Protocol + 对抗式风险表已关闭 |
| 「语言差不多了」 | M2 conformance 表 met/total + 0 p0 |
| 「插件系统有了」 | P01–P08 全 met + 样例社区插件 + 故障隔离测试 |
| 「领域也能做了」 | domain_manifest 参考向量 0 xfail |
| 「产品形态齐了」 | Workbench 布局准则 + E2E 录像，而非仅两栏 notebook |

公开 GitHub、CI、`EPIC-NNN` 证据包，把叙事压回证据。骄傲可以有，但骄傲必须可复查。

---

## 5. 给 Tech Leads / CTOs 的带走清单

1. **先钉产品意图与非目标**，再谈技术栈；洁净室是战略选择，不是附录。  
2. **用 seams 保护演进速度**：array-first + Protocol 比「快速糊一个解释器」更贵，也更便宜（长期）。  
3. **把完成定义成证据事件**：Issues、有序 Epic、双 tip、CI `test`、conformance/xfail。  
4. **分层验收商业风险**：宿主加载、桌面壳、领域向量，三者不可互换。  
5. **社区契约优先于专有幻觉**：能公开承诺的边界，才是可扩张的边界。  
6. **保留叫停权**：出口标准满足时，继续做广度必须是显式决策，而不是默认惯性。

---

## 6. 附录：从哪里看证据

| 材料 | 路径 / 链接 |
|------|-------------|
| 仓库 | https://github.com/superche/openmatlab |
| 协作原则 | `AGENTS.md` |
| 流程 / Epic 验收 | `docs/PROCESS.md` |
| 架构与 seams | `docs/ARCHITECTURE.md` |
| QA 五层 | `docs/QA.md` |
| 插件契约 | `docs/design/PLUGIN-CONTRACT.md` |
| 里程碑 | `docs/milestones/M*.md` |
| 验收证据 | `docs/acceptance/EPIC-*.md` |
| 能力清单 | `docs/feature_map.yaml` |

---

*MIT © Shaw Che / superche · 分享稿随仓库演进；数字以 `main` 上里程碑与验收文档为准。*
