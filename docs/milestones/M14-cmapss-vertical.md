# M14 — C-MAPSS PHM vertical

GitHub milestone: https://github.com/superche/openmatlab/milestone/14

涡扇退化信号实验垂直。一名写 MATLAB 的 PHM 用户，用自己的脚本风格走完：下载 FD001、读表、预处理、退化指标、多面板图、导出。门禁是这条故事，不是语料通过率。

Approved by Shaw on 2026-10-23. Defaults: runtime download of the Zenodo archive (CC BY 4.0, DOI 10.5281/zenodo.15346912); never commit the zip or the extracted text; FD001 only; Octave or a published formula for later numeric goldens; corpus residuals and the core backlog do not block this milestone.

## Exit criteria

| # | Criterion | Priority | Epic | Status |
|---|-----------|----------|------|--------|
| V01 | Runtime download of `CMAPSSData.zip` from Zenodo, FD001 text extracted, cache gitignored, zip and txt never committed | p0 | #994 | **met** ([design](../design/EPIC-994-cmapss-fd001.md), [acceptance](../acceptance/EPIC-994.md)) |
| V02 | `train_FD001.txt` via `readtable`, 26 PHM08 names, height and unique units match the public FD001 scale | p0 | #994 | **met** ([design](../design/EPIC-994-cmapss-fd001.md), [acceptance](../acceptance/EPIC-994.md)) |
| V03 | Near-constant sensor drop and `smoothdata` on one unit | p0 | #995 | pending |
| V04 | Early/late means, sensor correlation, per-unit failure cycle or RUL, within a fixed tolerance | p0 | #996 | pending |
| V05 | Sensor-correlation `heatmap` | p0 | #997 | pending |
| V06 | One `tiledlayout` figure with titles, unit id, and the Saxena / Zenodo citation | p0 | #997 | pending |
| V07 | `exportgraphics` PNG and PDF that keep the title and colorbar | p0 | #998 | pending |
| V08 | The story runs in the Workbench window | p0 | #999 | pending |
| V09 | `demos/cmapss/` plus `docs/acceptance/` reproducible from the public archive | p0 | #999 | pending |
| V10 | Corpus and core backlog do not block the close; a real blocker is a labelled issue | p1 | #999 | pending |

## Epics

1. **V-E1 #994 (p0):** download and FD001 load — V01, V02. **This epic.**
2. **V-E2 #995 (p0):** `smoothdata` and near-constant drop — V03.
3. **V-E3 #996 (p0):** degradation metrics — V04.
4. **V-E4 #997 (p0):** `heatmap` and the lab-meeting figure — V05, V06.
5. **V-E5 #998 (p0):** PNG and PDF export quality — V07.
6. **V-E6 #999 (p0):** Workbench recording and the acceptance package — V08, V09, V10.

## Non-goals

Simulink, App Designer, and a full toolbox match. FD002–FD004 as exit criteria. MIT-BIH and CWRU. MathWorks binaries or screenshots as goldens. Pixel-identical MATLAB figures.

## Milestone progress

- Criteria met: **2 / 10** (V01, V02)
- Conformance: `tests/conformance/test_m14_v01_v02.py` (V01, V02). V03–V10 are later epics and have no scripts yet.
- Next: V-E2 #995.
