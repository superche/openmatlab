# M16 BBBC038 nuclei image vertical — timeline

**Milestone:** [BBBC038 nuclei image vertical](https://github.com/superche/openmatlab/milestone/16) · [`docs/milestones/M16-bbbc038-vertical.md`](../milestones/M16-bbbc038-vertical.md)  
**Opened:** 2026-10-23 (Asia/Shanghai), Shaw approved the Defaults as a block.  
**Rule:** The Broad zip and the PNGs are not in the repository. Epics #1020–#1025 stay open until Shaw accepts them.

## 中文摘要

M16 在 2026-10-23 打开。范围只到 Broad BBBC038v1 的 `stage1_test.zip`（9545388 字节），运行时下载到 `downloads/bbbc038/`，不入库。许可 CC0 1.0，引用 Caicedo 等 Nature Methods 2019（doi:10.1038/s41592-019-0612-7）和 BBBC038v1。I-E1（#1020）已落地：校验 zip 大小，并用 `imread` 读入 1 个 FOV（盘上 8-bit RGBA，读出 uint8 RGB，256×256×3）。I-E2（#1021）已落地：同一 FOV 用全局 Otsu（`level = 22/255`）和 `bwareaopen`（`P = 50`，8 连通）得到掩膜，前景像素从 1003 降到 978，并排显示原图和掩膜。I-E3（#1022）已落地：同一掩膜上 `bwlabel` / `bwconncomp` 计数为 6，`regionprops` 给出面积、质心和偏心率，平均面积 163，中位数 153，并另开一幅面积直方图。`stage1_test` 没有掩膜文件，计数容差为 0。I-E4（#1023）已落地：同一 FOV 的 2×2 组会图包含原图、`labeloverlay` 叠加、面积直方图和计数摘要，脚注为 CC0、Caicedo 等 2019 和 BBBC038v1。I-E5（#1024）已落地：同一组会图在关闭前以 300 dpi 导出 PNG 和 PDF，标题和脚注留在裁切之内，文件在 `demos/bbbc038/out/`，不入库。V01–V07 证据在 [EPIC-1020](EPIC-1020.md)、[EPIC-1021](EPIC-1021.md)、[EPIC-1022](EPIC-1022.md)、[EPIC-1023](EPIC-1023.md) 和 [EPIC-1024](EPIC-1024.md)。Epic 保持打开，等 Shaw 批量验收。下一项是 I-E6（#1025）Workbench 录屏和验收包。本里程碑不开始 I-E6。

## Timeline

| Date | What |
|---|---|
| 2026-10-23 | Milestone/16 opened. Epics [#1020](https://github.com/superche/openmatlab/issues/1020)–[#1025](https://github.com/superche/openmatlab/issues/1025). Defaults locked: `stage1_test.zip` only, runtime download, no committed bytes. |
| 2026-10-23 | I-E1 in progress, then landed. V01 and V02 evidence: [EPIC-1020](EPIC-1020.md). The milestone table marks those two rows met. Epics stay open. |
| 2026-10-23 | I-E2 landed. V03 evidence: [EPIC-1021](EPIC-1021.md). Global Otsu plus `bwareaopen` (`P = 50`) and a 1-by-2 before/after panel. Epics stay open. |
| 2026-10-23 | I-E3 landed. V04 and V05 evidence: [EPIC-1022](EPIC-1022.md). Count 6, mean area 163, median 153, area histogram on its own figure. Epics stay open. |
| 2026-10-23 | I-E4 landed. V06 evidence: [EPIC-1023](EPIC-1023.md). 2×2 lab figure with `labeloverlay`, area histogram, summary, and the CC0 / Caicedo 2019 / BBBC038v1 footnote. Epics stay open. |
| 2026-10-23 | I-E5 landed. V07 evidence: [EPIC-1024](EPIC-1024.md). 300 dpi PNG and PDF of that lab figure. The crop keeps the title and the footnote. Epics stay open. |

## Still open

V08–V10. Next p0 is V08, [#1025](https://github.com/superche/openmatlab/issues/1025) (Workbench recording and the acceptance package). /9 and corpus residuals do not block close. This milestone does not start I-E6.
