# Acceptance evidence — Epic #5 (#63)

**Epic:** [#63 Single-quote char + cell arrays](https://github.com/superche/openmatlab/issues/63)  
**Scope issues:** [#64](https://github.com/superche/openmatlab/issues/64) · [#65](https://github.com/superche/openmatlab/issues/65) · [#66](https://github.com/superche/openmatlab/issues/66) · [#67](https://github.com/superche/openmatlab/issues/67)  
**Functional tip** (steps 1–3 code complete, PR #77): `8a6872c328d9591d81f0c6cb34e88b2209dd0026`  
**Evidence merge tip** (EPIC-005 + sync merged, PR #84): `e1e0cc9ea0952d01946dcd669f31ad355f8fe84c`  
**Captured:** 2026-10-11 18:21 CST on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Verdict

**Ready for user acceptance.** Ordered steps 1–5 green. Single-quote char is context-sensitive vs transpose; cell literals + content indexing + `cell(m,n)` shipped. Tests were **not** weakened.

## Traceability

| Step | Issue | PR | Merge commit | CI `test` |
|------|-------|-----|--------------|-----------|
| 1 | #64 char vs transpose | [#68](https://github.com/superche/openmatlab/pull/68) | `deb6f3044789b7f039895632bdf91bda1fe579bf` | pass |
| 2 | #65 cell literals | [#76](https://github.com/superche/openmatlab/pull/76) | `a1ea75e303a0878714334ac17a54832e8729f631` | pass |
| 3 | #66 cell index + cell() | [#77](https://github.com/superche/openmatlab/pull/77) | `8a6872c328d9591d81f0c6cb34e88b2209dd0026` | pass |
| 4–5 | #67 sync + EPIC-005 | [#84](https://github.com/superche/openmatlab/pull/84) | `e1e0cc9ea0952d01946dcd669f31ad355f8fe84c` | pass |

## Feature map

`lang.char_literal`, `runtime.char_value`, `lang.cell_literal`, `runtime.cell_value`, `lang.cell_index` → **done** per
`docs/design/ITER-067-epic5-done-criteria.md`. Counts: **done=34, partial=9, stub=2**.

## Measurable gate — pytest

At functional tip `8a6872c`:

```text
$ pytest -m "unit or bdd" --tb=no
174 passed, 2 deselected
```

## Smoke — CLI transcripts (functional tip `8a6872c`)

```text
$ openmatlab -e "s = 'a''b'"
s =

a'b

$ openmatlab -e "B = [1 2]'"
B =

[[1.]
 [2.]]

$ openmatlab -e "c = {1, 'z'}; x = c{1,2}"
x =

z

$ openmatlab -e "c = {1, 'z'; 2, [3 4]}; y = c{3}"
y =

z

$ openmatlab -e "d = cell(2,2)"
d =

{2x2 cell}
  (1,1) = []
  (1,2) = []
  (2,1) = []
  (2,2) = []

$ openmatlab -e "e = {}"
e =

{}  (empty cell)
```

Note: `c{3}` is column-major linear index into the 2×2 cell (`{1}=1`, `{2}=2`, `{3}=z`, `{4}=[3 4]`).

## Residual (canonical Issues — PROCESS § Residual Issues)

Filed on epic [#63](https://github.com/superche/openmatlab/issues/63) comment:

| Residual | Issue |
|----------|-------|
| `string` class vs CharValue | [#78](https://github.com/superche/openmatlab/issues/78) |
| Cell assignment / growing | [#79](https://github.com/superche/openmatlab/issues/79) |
| Comma-separated lists | [#80](https://github.com/superche/openmatlab/issues/80) |
| `cellfun` | [#81](https://github.com/superche/openmatlab/issues/81) |
| `c(i)` cell slice | [#82](https://github.com/superche/openmatlab/issues/82) |
| Char arithmetic / concat | [#83](https://github.com/superche/openmatlab/issues/83) |
| N-D cells (>2) | [#74](https://github.com/superche/openmatlab/issues/74) |

## How to re-run

```bash
git checkout e1e0cc9ea0952d01946dcd669f31ad355f8fe84c   # evidence merge tip (functional: `8a6872c328d9591d81f0c6cb34e88b2209dd0026`)
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab -e "c = {1, 'z'}; x = c{1,2}"
```
