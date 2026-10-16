# Acceptance evidence: Epic #768 (G-E1 graphics handle model upgrade)

**Epic:** [#768](https://github.com/superche/openmatlab/issues/768)  
**Feature PR:** [#850](https://github.com/superche/openmatlab/pull/850) (#768, #851)  
**Milestone:** [Graphics completion (M13)](https://github.com/superche/openmatlab/milestone/13) · [`docs/milestones/M13-graphics.md`](../milestones/M13-graphics.md)  
**Design + adversarial review:** [`docs/design/EPIC-768-handle-model.md`](../design/EPIC-768-handle-model.md)  
**Captured:** 2026-10-17 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `370a6620c431cd5148f390c1b3f914ae673232c4` | Squash merge of feature PR [#850](https://github.com/superche/openmatlab/pull/850) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M13 criterion G01 is **met**. Epic #768 stays **open** until the user accepts it.

Graphics handles are now handle arrays that keep the model through indexing, transpose, concatenation, growth and deletion, `for` loops and `arrayfun`. `class(h)` returns the full MATLAB class name (`matlab.graphics.chart.primitive.Line`, `matlab.graphics.axis.Axes`, `matlab.ui.Figure`, ...), `h(k).Prop` reads and writes, `[h.Prop]` collects a cs-list, `isvalid`/`isgraphics`/`delete` work element-wise, `gobjects` makes placeholder arrays, and handles display as `Line with properties:`. `double(h)` stays numeric. Traceability follow-up: [#852](https://github.com/superche/openmatlab/pull/852).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| G-E1 epic: handle arrays, class names, h(k).Prop, display | #768 | [#850](https://github.com/superche/openmatlab/pull/850) | [job 117158401546](https://github.com/superche/openmatlab/actions/runs/38955853014/job/117158401546) **success** |
| residual | #851 | [#850](https://github.com/superche/openmatlab/pull/850) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "figure('Visible','off'); h = plot(1:3, [1:3; 2:4]'); h(2).LineWidth = 3; disp(class(h)); disp([h.LineWidth]); disp(h(1)); close all"
matlab.graphics.chart.primitive.Line
   0.5000   3.0000
  Line with properties:

         Color: [0 0.447 0.741]
     LineStyle: '-'
     LineWidth: 0.5
        Marker: 'none'
    MarkerSize: 6
         XData: [1 2 3]
         YData: [1 2 3]

  Show all properties
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1955 passed, 2 deselected, 12 xfailed in 66.16s (0:01:06)
$ pytest tests/unit/test_epic768_handle_arrays.py tests/bdd/test_graphics_handle_arrays_bdd.py "tests/conformance/test_m13_conformance.py::test_m13_criterion[G01-m13_g01_handle_arrays]" --tb=no
12 passed in 1.34s
$ pytest tests/conformance/test_m13_conformance.py --tb=no
2 passed, 9 xfailed in 0.73s
```

New cases: `tests/unit/test_epic768_handle_arrays.py` (9), `tests/bdd/test_graphics_handle_arrays_bdd.py` (2); G01 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.graphics.handle_arrays
libs.graphics.handle_arrays      libs       done     graphics handle arrays and MATLAB class names
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| `properties(h)`/`methods(h)` for graphics; `get(h)` on handle arrays; confirm `h.Prop = v` on arrays | [#851](https://github.com/superche/openmatlab/issues/851) |

## Milestone progress (M13)

- Criteria met: **1 / 10** (G01)
- Conformance scripts passing: **1 / 10** (strict xfail pending: G02, G03, G04, G05, G06, G07, G08, G09, G10)
- Next: G-E5 #772 and G-E4 #771 (largest corpus `graphics` groups), then G-E2 #769, G-E3 #770, G-E6 #773, G-E7 #774; M12 C-E5 #765.
