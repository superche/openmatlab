# Epic #771 (M13 G-E4): colour/image and 3-D plotting

Milestone: [M13 Graphics completion](../milestones/M13-graphics.md), criteria G05 and G06.

## Problem

3-D plotting functions (`plot3`, `surf`, `mesh`, `sphere`, `view`...) were undefined, and so were `imshow`, the tick helpers (`xticks`...), `daspect` and `uistack`. Function handles to frame intrinsics (`@ishandle`, `@isvarname`) failed with `undefined function`. Colormap tables, `colorbar`, `image`/`imagesc` and `caxis`/`clim` came with Epic #772.

## Design

- New module `libs/chart3d_builtins.py`, registered after `chart_builtins`. Its functions are `plot3`, `scatter3`, `surf`/`surfc`/`mesh`/`meshc`/`waterfall`/`surface`, `contour3`, `bar3`, `sphere`/`cylinder`/`ellipsoid` (outputs, or a surface when called with none), `view` (`view(2)`, `view(3)` = [-37.5 30], `[az el]`, `[x y z]`, `[az, el] = view`), `zlim`, `shading`, `light`/`camlight`, `lighting`/`material` (accepted options, no effect), `imshow` (numeric/logical/uint8/uint16 data only), `daspect`/`pbaspect`, `clabel`, `uistack`, and `xticks`/`yticks`/`zticks`/`xticklabels`/...
- Plotting a 3-D object switches a 2-D axes to the default 3-D view. `ZLim` auto-scales from the `ZData` of the axes children.
- `surf`/`mesh` give `matlab.graphics.chart.primitive.Surface`, while `pcolor`/`surface` keep `matlab.graphics.primitive.Surface` (MATLAB distinguishes the two). This uses a per-object class override (`_cls`).
- Rendering is a best-effort 2-D projection (`pcolormesh` of `CData`). The handle model is the contract. Pixel snapshots belong to G10 (#774).
- `@name` for a frame intrinsic now creates a handle that calls the intrinsic with the caller's evaluator.

## Adversarial review

| Attack | Result |
|---|---|
| `plot3` with 2 args or mismatched lengths, `surf` with bad grid sizes, `view(7)`, `zlim([2 1])`, `shading wobbly`, `xticks([3 1])`, `imshow('cat.png')`, `sphere(0)` | MATLAB-style errors, no traceback |
| `pcolor` class after `surf` exists | Still `matlab.graphics.primitive.Surface` (Epic #772 test unchanged) |
| `cellfun(@isvarname, ...)` | Works |
| Rendering surfaces and lights and saving to png | No crash |
| Full test suite | Unchanged existing tests all pass |

## G05 status (stopped, needs Shaw)

G05 check `c1` expects `size(colormap(parula)) == [256 3]`: MATLAB colormap functions called with no argument return as many colours as the current figure's colormap, 256 by default. The Epic #772 unit test `test_colormaps_are_clean_room_tables` (already on `main`) asserts that `colormap(jet); m = colormap;` gives 64 rows. Changing the default to 256 means changing that existing test, which the delivery rules forbid without approval. G05 therefore stays **pending**, and the other five G05 checks pass. See the acceptance record.
