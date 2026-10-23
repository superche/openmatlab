# M15 MIT-BIH Arrhythmia vertical — timeline

**Milestone:** [MIT-BIH Arrhythmia vertical](https://github.com/superche/openmatlab/milestone/15) · [`docs/milestones/M15-mitbih-vertical.md`](../milestones/M15-mitbih-vertical.md)  
**Opened:** 2026-10-23 (Asia/Shanghai), Shaw approved the Defaults as a block.  
**Rule:** Raw PhysioNet files are not in the repository. Epics #1008–#1013 stay open until Shaw accepts them.

## 中文摘要

M15 在 2026-10-23 打开。范围只到 PhysioNet MIT-BIH 记录 100（`100.hea` / `100.dat` / `100.atr`），运行时下载到 `downloads/mitbih/`，不入库。许可 ODC-By 1.0，引用 Moody & Mark DOI 10.13026/C2F305、IEEE EMB 2001，以及 Goldberger 等 Circulation 2000。B-E1（#1008）加载器已落地，V01/V02 证据在 [EPIC-1008](EPIC-1008.md)。Epic 保持打开，等 Shaw 批量验收。下一项是 B-E2（#1009）零相位带通。

## Timeline

| Date | What |
|---|---|
| 2026-10-23 | Milestone/15 opened. Epics [#1008](https://github.com/superche/openmatlab/issues/1008)–[#1013](https://github.com/superche/openmatlab/issues/1013). Defaults locked: record 100 only, runtime download, no committed bytes. |
| 2026-10-23 | B-E1 in progress, then landed. V01 and V02 evidence: [EPIC-1008](EPIC-1008.md). The milestone table marks those two rows met. Epics stay open. |

## Still open

V03–V10. Next p0 is V03, [#1009](https://github.com/superche/openmatlab/issues/1009) (`filtfilt` / `bandpass`, about 0.5–40 Hz). /9 and corpus residuals do not block close.
