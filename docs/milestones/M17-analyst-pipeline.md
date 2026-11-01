# M17 — Analyst pipeline

GitHub milestone: https://github.com/superche/openmatlab/milestone/17

**Related:**

- Epic [#1032](https://github.com/superche/openmatlab/issues/1032). Approved cut 2026-10-31 (bundle-A).
- Children: [#1033](https://github.com/superche/openmatlab/issues/1033) missing values (closed), [#721](https://github.com/superche/openmatlab/issues/721) CSV `TreatAsMissing` (closed), [#742](https://github.com/superche/openmatlab/issues/742) `IncludeEmptyGroups` (In slice on this branch; the rest is Core backlog), [#1034](https://github.com/superche/openmatlab/issues/1034) this story.
- Not a fourth vertical. Corpus pass rate is not a gate. Milestone/9 is not cleared.
- Package: [`../acceptance/M17-analyst-pipeline.md`](../acceptance/M17-analyst-pipeline.md).

## Intent

A person who already writes MATLAB washes one messy CSV in the OpenMATLAB Workbench: read it, see what is missing, drop or fill those cells, summarise by group (including a category that never occurs), and take the CSV away.

The gate is that story.

## Exit criteria (measurable)

M17 is **done** only when **all** of A01–A06 hold on `main`. There is no conformance manifest and no corpus-% threshold.

| # | Criterion | Demo | Priority | Issue | Status |
|---|---|---|---|---|---|
| A01 | `ismissing`, `rmmissing`, and `fillmissing` with `constant`, `previous`, and `next`. Other fill methods stay an error. | unit tests for #1033 / #1039 | p1 | [#1033](https://github.com/superche/openmatlab/issues/1033) | met |
| A02 | `readtable` CSV `'TreatAsMissing'`. A spreadsheet path still errors. xlsx is an explicit non-goal. | unit tests for the #721 slice | p1 | [#721](https://github.com/superche/openmatlab/issues/721) | met |
| A03 | `groupsummary(..., 'IncludeEmptyGroups', true)` keeps an unused categorical category. Story methods are `mean`, `sum`, `min`, `max`, `std`, plus `GroupCount`. | `tests/unit/test_groupsummary_empty.py` | p1 | [#742](https://github.com/superche/openmatlab/issues/742) | met on this branch (PR #1057). Not on `main` until that PR merges. |
| A04 | `demos/analyst` one-shot: `readtable` → `ismissing` → `rmmissing` / `fillmissing` → `groupsummary` with `IncludeEmptyGroups` → `writetable` CSV under `out/`. | [`../../demos/analyst/story_assays.m`](../../demos/analyst/story_assays.m) | p1 | [#1034](https://github.com/superche/openmatlab/issues/1034) | met on this branch. Not on `main` yet. |
| A05 | Acceptance package: Workbench recording, `docs/acceptance` text, and the `.m`. A third party reruns from tip `main` once this branch and #1057 have merged. | [`../acceptance/EPIC-1034.md`](../acceptance/EPIC-1034.md) | p1 | [#1034](https://github.com/superche/openmatlab/issues/1034) | met on this branch. Not on `main` yet. |
| A06 | Close does not require a corpus-% rise or an empty milestone/9. No `m17-blocker` issue. | note in the acceptance package | p1 | [#1032](https://github.com/superche/openmatlab/issues/1032) | met |

## Progress snapshot

**6 / 6** criteria are evidenced on branch `cursor/analyst-story-acceptance-1a5c`. **2 / 6** are on `main` today (A01, A02). A03 is the unmerged PR #1057. A04 and A05 are this branch. A06 is the close rule and holds.

GitHub milestone/17 stays **open**. Epic #1032 is the open `p0`. #742 stays open for the bullets that moved to the Core backlog (#1052, #1053, #1054, #1055, #1056). This table does not close them.

## Non-goals

xlsx and other spreadsheet I/O. `detectImportOptions`. `fillmissing` methods other than `constant`, `previous`, and `next`. A fourth vertical. Corpus percentage. Clearing milestone/9. `publish` / report generators. Simulink, App Designer, toolbox parity.
