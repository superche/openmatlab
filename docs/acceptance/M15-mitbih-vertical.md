# M15 MIT-BIH Arrhythmia vertical — timeline

**Milestone:** [MIT-BIH Arrhythmia vertical](https://github.com/superche/openmatlab/milestone/15) · [`docs/milestones/M15-mitbih-vertical.md`](../milestones/M15-mitbih-vertical.md)  
**Opened:** 2026-10-23 (Asia/Shanghai), Shaw approved the Defaults as a block.  
**Rule:** Raw PhysioNet files are not in the repository. Epics #1008–#1013 stay open until Shaw accepts them.

## 中文摘要

M15 在 2026-10-23 打开。范围只到 PhysioNet MIT-BIH 记录 100（`100.hea` / `100.dat` / `100.atr`），运行时下载到 `downloads/mitbih/`，不入库。许可 ODC-By 1.0，引用 Moody & Mark DOI 10.13026/C2F305、IEEE EMB 2001，以及 Goldberger 等 Circulation 2000。B-E1（#1008）加载器已落地，V01/V02 证据在 [EPIC-1008](EPIC-1008.md)。B-E2（#1009）用 `filtfilt` 对 MLII 做 0.5–40 Hz 零相位带通，V03 证据在 [EPIC-1009](EPIC-1009.md)。B-E3（#1010）在滤波后的 MLII 上做 `findpeaks`、RR 直方图和 `fft` 频谱，V04/V05 证据在 [EPIC-1010](EPIC-1010.md)。B-E4（#1011）把同一组序列画进一张 2×2 `tiledlayout`，脚注引用 DOI、Moody & Mark 2001 和 Goldberger 等 2000，V06 证据在 [EPIC-1011](EPIC-1011.md)。Epic 保持打开，等 Shaw 批量验收。下一项是 B-E5（#1012）导出 PNG 与 PDF。

## Timeline

| Date | What |
|---|---|
| 2026-10-23 | Milestone/15 opened. Epics [#1008](https://github.com/superche/openmatlab/issues/1008)–[#1013](https://github.com/superche/openmatlab/issues/1013). Defaults locked: record 100 only, runtime download, no committed bytes. |
| 2026-10-23 | B-E1 in progress, then landed. V01 and V02 evidence: [EPIC-1008](EPIC-1008.md). The milestone table marks those two rows met. Epics stay open. |
| 2026-10-23 | B-E2 landed. V03 evidence: [EPIC-1009](EPIC-1009.md). MLII is bandpass-filtered at 0.5–40 Hz with `filtfilt`; raw and filtered share one axes. Epics stay open. |
| 2026-10-23 | B-E3 landed. V04 and V05 evidence: [EPIC-1010](EPIC-1010.md). Filtered MLII gets `findpeaks`, an RR histogram, and an `fft` amplitude spectrum. Epics stay open. |
| 2026-10-23 | B-E4 landed. V06 evidence: [EPIC-1011](EPIC-1011.md). One 2×2 `tiledlayout` holds raw MLII, filtered R peaks, RR in seconds, and the spectrum, with the citation footnote. Epics stay open. |

## Still open

V07–V10. Next p0 is V07, [#1012](https://github.com/superche/openmatlab/issues/1012) (`exportgraphics` PNG and PDF). /9 and corpus residuals do not block close.
