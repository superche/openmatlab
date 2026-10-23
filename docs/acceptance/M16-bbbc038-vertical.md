# M16 BBBC038 nuclei image vertical — timeline

**Milestone:** [BBBC038 nuclei image vertical](https://github.com/superche/openmatlab/milestone/16) · [`docs/milestones/M16-bbbc038-vertical.md`](../milestones/M16-bbbc038-vertical.md)  
**Opened:** 2026-10-23 (Asia/Shanghai), Shaw approved the Defaults as a block.  
**Rule:** The Broad zip and the PNGs are not in the repository. Epics #1020–#1025 stay open until Shaw accepts them.

## 中文摘要

M16 在 2026-10-23 打开。范围只到 Broad BBBC038v1 的 `stage1_test.zip`（9545388 字节），运行时下载到 `downloads/bbbc038/`，不入库。许可 CC0 1.0，引用 Caicedo 等 Nature Methods 2019（doi:10.1038/s41592-019-0612-7）和 BBBC038v1。I-E1（#1020）已落地：校验 zip 大小，并用 `imread` 读入 1 个 FOV（盘上 8-bit RGBA，读出 uint8 RGB，256×256×3）。V01/V02 证据在 [EPIC-1020](EPIC-1020.md)。Epic 保持打开，等 Shaw 批量验收。下一项是 I-E2（#1021）`imbinarize` + `bwareaopen`。本里程碑不开始 I-E2。

## Timeline

| Date | What |
|---|---|
| 2026-10-23 | Milestone/16 opened. Epics [#1020](https://github.com/superche/openmatlab/issues/1020)–[#1025](https://github.com/superche/openmatlab/issues/1025). Defaults locked: `stage1_test.zip` only, runtime download, no committed bytes. |
| 2026-10-23 | I-E1 in progress, then landed. V01 and V02 evidence: [EPIC-1020](EPIC-1020.md). The milestone table marks those two rows met. Epics stay open. |

## Still open

V03–V10. Next p0 is V03, [#1021](https://github.com/superche/openmatlab/issues/1021) (`imbinarize` / `bwareaopen`). /9 and corpus residuals do not block close.
