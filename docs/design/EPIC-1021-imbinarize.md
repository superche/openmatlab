# Epic #1021 (I-E2): imbinarize and bwareaopen on one BBBC038 FOV

Milestone: [M16 BBBC038 nuclei image vertical](../milestones/M16-bbbc038-vertical.md), criterion V03.

## Problem

After one stage1_test field of view is in memory, the scientist wants a binary mask they can put next to the raw image. The path is the default global threshold plus an area opening, with the numbers written down so the same script produces the same mask.

## Design

- **`graythresh(I)`.** 256-bin Otsu. The dark class is bins `0..t` and the bright class is `t+1..255`. The returned level is `t/255`, the split that maximizes between-class variance. Ties take the smallest `t`. A constant image has variance 0 on every split, so `t` is 0. Float images are clipped to `[0, 1]` before binning. uint16 is scaled into those 256 bins.
- **`imbinarize(I)`.** Same as `imbinarize(I, graythresh(I))`. RGB is reduced with the published `rgb2gray` weights 0.2989, 0.5870, and 0.1140. uint8 and uint16 results are rounded back to that class. Foreground is `im2double(gray) > level` (strictly greater). `imbinarize(I, T)` takes one scalar `T` in `[0, 1]`. `imbinarize(I, 'global')` is the Otsu call.
- **`bwareaopen(BW, P)`.** Nonzero finite pixels are foreground. 8-connected components with area strictly less than `P` are removed. `bwareaopen(BW, P, conn)` allows `conn` 4 or 8. The output is logical and the same size. Labeling is internal. `bwlabel`, `bwconncomp`, and `regionprops` are not registered.
- **Story.** `demos/bbbc038/story_stage1_test.m` still prints the V01 and V02 lines. It then prints the level, `P`, the foreground count, and the count after opening. A `tiledlayout(1, 2)` shows `imshow` of the raw FOV and of the mask, both with equal data aspect and reverse Y.

On the demo FOV the three channels are equal, so the gray image is that channel. Otsu returns `t = 22` (`level = 22/255`). The 8-connected component areas are 1, 24, 117, 143, 152, 154, 193, and 219. `P = 50` sits in the gap between 24 and 117. Foreground pixels go from 1003 to 978. Those counts are the V03 pin. This epic does not print a nucleus count.

Citation stays with the story: CC0 1.0, Caicedo et al., Nature Methods 2019, BBBC038v1. The zip and the PNG stay in `downloads/bbbc038/`.

## Non-goals

The adaptive method, a threshold matrix, sensitivity name-value pairs, 3-D images, and connectivity matrices. Deep learning and GPU. `bwlabel` / `bwconncomp` / `regionprops` (I-E3, [#1022](https://github.com/superche/openmatlab/issues/1022)). The lab-meeting figure, 300 dpi export, and the Workbench recording (I-E4…I-E6). Pixel parity with a MATLAB release's tie break. This is not a copy of the Octave image package.

## Adversarial review

| Attack | Result |
|---|---|
| `'adaptive'` or a threshold matrix | `OpenMATLAB:imbinarize:Adaptive` or `OpenMATLAB:imbinarize:ThresholdMatrix` |
| `T` outside `[0, 1]` | `OpenMATLAB:imbinarize:ThresholdRange` before a mask is returned |
| Tie between Otsu splits | Smallest `t`. Half 0 and half 255 returns level 0, and `>` still separates 0 from 255 |
| Constant image | Level 0. Zeros stay false. A nonzero constant becomes true |
| uint8 threshold 0.5 | 127 is false (`127/255 < 0.5`). 128 is true |
| RGB with equal channels | `rgb2gray` rounds back to that channel. `imbinarize` matches the 2-D call |
| Diagonal pair, `P = 2` | 8-connected keeps both pixels. 4-connected removes both |
| Area equal to `P` | Kept. Area `P - 1` is removed |
| `conn` 6 or a 3-by-3 matrix | `OpenMATLAB:bwareaopen:Connectivity` |
| 3-D input to `bwareaopen` | `OpenMATLAB:bwareaopen:Dimension` |
| Story grows a nucleus count | It prints pixel counts only. Component areas are documented here, not returned as `regionprops` |
| Existing tests | Not modified. The V01/V02 conformance test still runs this story and still checks the same scalars |
