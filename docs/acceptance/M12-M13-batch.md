# M12 + M13 batch acceptance (screen recordings)

**Captured:** 2026-10-23 (Asia/Shanghai) on `/workspace/openmatlab`; M13 video re-take after Shaw rejection (Figures panel switching)  
**Rule:** Videos are real GUI / real commands (ffmpeg x11grab on `DISPLAY=:2`). None are invented.  
**Chinese note (outside repo):** `/workspace/proposals/M12-M13-acceptance-evidence.md`  
**Copies for Shaw:** `/workspace/recordings/showcase_m12_corpus.mp4`, `/workspace/recordings/showcase_m13_graphics.mp4`

Epics **#765–#774** remain **OPEN** until Shaw accepts. Milestones M12 / M13 stay open.

## Videos

| Milestone | Video | Duration | Proves |
|---|---|---|---|
| M12 | [`demos/corpus/showcase_m12_corpus.mp4`](../../demos/corpus/showcase_m12_corpus.mp4) | ~71 s | REPORT T0/T1/T2/T3 (C08 75.3 %); two real T3 goldens; pytest 11/11 |
| M13 | [`demos/workbench/showcase_m13_graphics.mp4`](../../demos/workbench/showcase_m13_graphics.mp4) | ~147 s | G09 output + **Figures panel click-switch** (4 figs), G05 colour, G03 layout, G08 `.fig`, G10 46 snapshots |

## Scene timestamps

### M12 (`showcase_m12_corpus.mp4`)

| t | Scene |
|---|---|
| 0–4 s | Title — Epic #765 / C07+C08 / M12 10/10 |
| 4–22 s | `docs/corpus/REPORT.md` head — T0 99.5 %, T1 70.5 %, T2 82.8 %, **T3 75.3 %** |
| 22–30 s | Deprompted T3 sample source (`t3_Boolean_values_1.m`) |
| 30–42 s | `openmatlab run` Boolean_values/1 |
| 42–55 s | `openmatlab run` Sum_and_product_of_an_array/1 |
| 55–71 s | `pytest tests/conformance/test_m12_conformance.py` → 11 passed |

Detail: [`EPIC-765.md`](EPIC-765.md). Re-record: `DISPLAY=:2 ./demos/corpus/record_m12_corpus_showcase.sh`.

### M13 (`showcase_m13_graphics.mp4`) — re-recorded 2026-10-23 (interactive figure switch)

| t | Scene |
|---|---|
| 0–20 s | **G09/#767** fprintf/disp → Command Window |
| 20–37 s | **G09/#774** create **4** docked figures (plot / imagesc / tiled / surf); Refresh |
| **41.8 s** | **切换 Figure 1** — list click → `*` + preview; CW gcf → 1 |
| **50.3 s** | **切换 Figure 2** — list click → focused=2; CW → 2 |
| **58.8 s** | **切换 Figure 3** — list click → focused=3; CW → 3 |
| **67.3 s** | **切换 Figure 4** — list click → focused=4; CW → 4 |
| 77–94 s | **G05** colormap 256 / imagesc / colorbar |
| 94–111 s | **G03** tiledlayout / yyaxis |
| 111–128 s | **G08** savefig/openfig `.fig` round-trip |
| 128–147 s | **G10** 46 golden snapshots path |

Detail: [`EPIC-774.md`](EPIC-774.md) (covers G09 halves from #767+#774). Re-record: `DISPLAY=:2 ./demos/workbench/record_m13_graphics_showcase.sh`.

## Related acceptance packages (still open)

M12: #765 (this video), #761–#764, #766.  
M13: #767–#774 (this video anchors G09/G05/G03/G08/G10; other epics keep their written packages).
