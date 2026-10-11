# AGENTS.md — OpenMATLAB 协作原则

面向人类与 agent 的短原则。流程细节见 `docs/PROCESS.md`、`docs/QA.md`。

## 第一性原理

- **做法本身错了 → 停下来从第一性原理重想**，不要在错误抽象上堆补丁。
- 产品目标：矩阵优先的 MATLAB 兼容工作台（洁净室 / 公开规格），不是通用软件工程 IDE，也不是逆向 MATLAB。

## 编码

- **KISS**：能简单就简单；先让接口对，再优化。
- **里氏替换（LSP）**：实现 `Value` / `Array` / `ArrayBackend` 等协议时，子类型不得破坏调用方假设。
- **高内聚 / 低耦合**：按 `host` / `lang` / `runtime` / `numerics` / `graphics` / `libs` / `qa` 分包；跨包只依赖稳定 Protocol，不绕过 seams。

## 代码审查

- **奥卡姆剃刀**：同等效果下选更简单的设计与更小的 diff。
- **Deslop**：删噪声优于耍聪明（无用抽象、冗长注释、投机取巧的兼容层）。本环境若无 Cursor deslop skill，仍按此意图执行：去掉 slop，留下清晰小改动。

## QA（不可妥协）

- **测试服务需求**：用例对齐 `docs/feature_map.yaml`、`docs/test_catalog.yaml`、Gherkin、Issue 验收标准。
- **禁止**为了让流水线变绿而削弱 / 篡改用例去迁就错误实现。
- 若需求本身要改：在 **Issue/PR 中写明理由**，同步改 feature map / catalog / Gherkin，再改代码。

## 每次迭代清单

1. 更新 `feature_map` + `test_catalog`（+ 相关 Gherkin）
2. 短技术设计（`docs/design/` 或 PR 正文）
3. 实现（经 PR；`main` 受保护，检查名 **`test`**）
4. 对抗式自审（对照本文件原则）
5. CI 绿再合并

工作项以 **GitHub Issues** 为准；`feature_map.yaml` 为同步清单。
