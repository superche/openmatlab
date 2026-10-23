# Epic #1022 (I-E3): bwlabel, bwconncomp, and regionprops

Milestone: [M16 BBBC038 nuclei image vertical](../milestones/M16-bbbc038-vertical.md), criteria V04 and V05.

## Problem

The opened mask from I-E2 is a binary image. The scientist needs a nucleus count, a short morphology table, and a histogram of the areas. `stage1_test.zip` has image files only (65 PNGs under `images/`, no `masks/`), so there is no contest mask to score.

## Design

- **`bwlabel(BW)` and `bwlabel(BW, conn)`.** Nonzero finite pixels are foreground. `conn` is 4 or 8; the default is 8. Labels are float64. Background is 0. Ids are assigned in column-major encounter order: down a column, then the next column to the right. The second output is the object count.
- **`bwconncomp(BW)` and `bwconncomp(BW, conn)`.** One struct: `Connectivity`, `ImageSize` as `[rows cols]`, `NumObjects`, and `PixelIdxList` (a column cell of 1-based column-major linear indices). The same labeler as `bwlabel`.
- **`regionprops`.** Properties in this slice are `Area`, `Centroid`, and `Eccentricity`. A logical image is labeled with 8-connectivity first. A numeric image is already a label matrix. A `bwconncomp` struct is read from `PixelIdxList`. The result is an N-by-1 struct array, one element per object, in label order.
- **Centroid.** `[x y]`, 1-based. `x` is the mean column, `y` is the mean row.
- **Eccentricity.** Let `x` and `y` be the column and row coordinates, centered on their means. `m20 = sum(x^2)`, `m02 = sum(y^2)`, `m11 = sum(x*y)`. `delta = sqrt((m20-m02)^2 + 4*m11^2)`. `λmax = (m20+m02+delta)/2`, `λmin = (m20+m02-delta)/2`. Eccentricity is 0 when `λmax` is 0, otherwise `sqrt(1 - λmin/λmax)`. A single pixel is 0. A straight run of pixels is 1.
- **Golden.** Tolerance on the count and on each area is 0. Eccentricity in the conformance test is recomputed from the label pixels with the formula above and must agree within `1e-9`. On the demo FOV the opened mask has 6 objects. Label order areas are 152, 219, 143, 117, 193, 154. The mean is 163 and the median is 153. Those six areas are the same set `bwareaopen` kept (117 and above).
- **Story.** `demos/bbbc038/story_stage1_test.m` keeps the V01–V03 lines and the 1-by-2 panel. It prints the count, one row per nucleus, then the mean, median, and mean eccentricity. `histogram(areas)` is a second figure titled `BBBC038 areas`. `figure(1)` makes the before/after panel current again, so the V03 check still sees that layout.

## Non-goals

Circularity and perimeter. BoundingBox and the rest of the `regionprops` property list. 3-D images and connectivity matrices. Contest scoring, `stage1_train` masks, and a deep-learning instance segmentation. The lab-meeting figure that puts the FOV, an overlay, this histogram, and a footnote on one `tiledlayout` is I-E4 ([#1023](https://github.com/superche/openmatlab/issues/1023)).

## Adversarial review

| Attack | Result |
|---|---|
| No mask in `stage1_test` | The golden is the labeling of the documented mask. Count and areas have tolerance 0 |
| 4-connected diagonal vs 8-connected | Two objects, or one object of area 2 |
| Label order | Column-major. A 4-connected pair in column 1 is object 1; a later pixel in column 2 is object 2 |
| `regionprops(L)` vs `regionprops(CC)` | Same areas and eccentricities |
| Two-pixel vertical line | Centroid `[1 1.5]`, eccentricity 1. A filled 2-by-2 block is eccentricity 0 |
| `Perimeter` or any other property | `OpenMATLAB:regionprops:BadProperty` |
| `conn` 6, a connectivity matrix, or a 3-D image | `OpenMATLAB:bwlabel:Connectivity` or `OpenMATLAB:bwlabel:Dimension` |
| Empty mask | Count 0 |
| Histogram replacing the V03 panel | The histogram is figure 2. `figure(1)` restores the 1-by-2 layout as the current figure |
| Existing tests | Not modified. The V03 conformance test still passes on this story |
