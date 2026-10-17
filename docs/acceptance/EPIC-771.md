# Acceptance evidence: Epic #771 (G-E4 3-D plotting, imshow, tick helpers)

**Epic:** [#771](https://github.com/superche/openmatlab/issues/771)  
**Feature PR:** [#861](https://github.com/superche/openmatlab/pull/861) (#771, #857)  
**Milestone:** [Graphics completion (M13)](https://github.com/superche/openmatlab/milestone/13) · [`docs/milestones/M13-graphics.md`](../milestones/M13-graphics.md)  
**Design + adversarial review:** [`docs/design/EPIC-771-colour-3d.md`](../design/EPIC-771-colour-3d.md)  
**Captured:** 2026-10-17 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `981c2797375a8f562d9358a676d9e5f4b2d581b1` | Squash merge of feature PR [#861](https://github.com/superche/openmatlab/pull/861) |
| Evidence merge tip | `ac5d2a89e9b87d9f0bc66be01b03aa6da98ad3fe` | Squash merge of [#867](https://github.com/superche/openmatlab/pull/867); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M13 criterion G06 is **met**. Epic #771 stays **open** until the user accepts it.

3-D plotting: `plot3`, `scatter3`, `surf`/`surfc`/`mesh`/`meshc`/`waterfall`/`surface`, `contour3`, `bar3`, `sphere`/`cylinder`/`ellipsoid`, `view`, `zlim`, `shading`, `light`/`camlight`/`lighting`/`material`. Also `imshow` (numeric/logical/integer data), `daspect`/`pbaspect`, `clabel`, `uistack`, the tick helpers (`xticks`, `yticklabels`, ...) and `@intrinsic` function handles (`@ishandle`, `@isvarname`). Rendering is a best-effort 2-D projection; the handle model is the contract. G06 is met. G05 was completed later by Shaw-approved [#982](https://github.com/superche/openmatlab/pull/982) (default colormap length 256; #866 closed). **G05 is met** on tip `47afebc`.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| G-E4 epic: 3-D plotting, imshow, tick helpers, @intrinsic handles | #771 | [#861](https://github.com/superche/openmatlab/pull/861) | [job 117187710003](https://github.com/superche/openmatlab/actions/runs/38964568077/job/117187710003) **success** |
| residual (xticks, imshow, @ishandle delivered) | #857 | [#861](https://github.com/superche/openmatlab/pull/861) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "figure('Visible','off'); [X,Y] = meshgrid(1:3); s = surf(X,Y,X+Y); disp(class(s)); [az,el] = view; disp([az el]); xticks([1 2 3]); disp(xticks); f = @isvarname; disp(f('abc')); close all"
matlab.graphics.chart.primitive.Surface
   -37.5000    30.0000
   1   2   3
1
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
2028 passed, 2 deselected, 8 xfailed in 71.90s (0:01:11)
$ pytest tests/unit/test_epic771_colour_3d.py "tests/conformance/test_m13_conformance.py::test_m13_criterion[G06-m13_g06_3d]" --tb=no
16 passed in 1.41s
$ pytest tests/conformance/test_m13_conformance.py --tb=no
6 passed, 5 xfailed in 1.71s
```

New cases: `tests/unit/test_epic771_colour_3d.py` (7); G06 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.graphics.plot3d
libs.graphics.plot3d             libs       done     3-D plotting, image display and axes helpers
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| G05 `c1`: default colormap size 256 vs existing 64-row test | [#866](https://github.com/superche/openmatlab/issues/866) |
| Pixel-accurate 3-D rendering | G-E7 [#774](https://github.com/superche/openmatlab/issues/774) (G10) |

## Milestone progress (M13)

- Criteria met: **10 / 10** (after G05 via #982 and later epics) (G01, G02, G04, G06, G07)
- Conformance scripts passing: **5 / 10** (strict xfail pending: G03, G05, G08, G09, G10)
- Next: G-E3 #770, G-E6 #773, G-E7 #774; M12 C-E5 #765; #766 corpus burndown.
