# BBBC038 stage1_test

Runtime download of one Broad BBBC038v1 test zip. The zip and the extracted FOV PNG are cached under `downloads/bbbc038/` and are not part of this repository.

```bash
openmatlab -e "run('demos/bbbc038/story_stage1_test.m')"
```

The story checks the zip size (9545388 bytes) and reads one field of view with `imread`. That PNG is 8-bit RGBA on disk. `imread` returns a uint8 RGB array, 256 by 256 by 3.

It then segments that FOV with global Otsu (`graythresh` / `imbinarize`) and `bwareaopen` at `P = 50` (8-connected). On this FOV the component areas are 1, 24, 117, 143, 152, 154, 193, and 219, so 50 drops the two small objects and keeps the rest. A 1-by-2 `tiledlayout` shows the raw FOV and the mask. The level on this FOV is 22/255. Foreground pixels go from 1003 to 978.

`bwlabel` and `bwconncomp` then count the 8-connected objects on that mask. `regionprops` reports Area, Centroid, and Eccentricity. This zip has no ground-truth masks, so the count is that labeling (tolerance 0). On this FOV the count is 6, the areas are 152, 219, 143, 117, 193, and 154 (label order), the mean area is 163, and the median is 153. A separate figure is the area histogram.

`labeloverlay` paints those six labels onto the FOV (default transparency 0.5). A 2-by-2 `tiledlayout` shows the raw FOV, the overlay, the area histogram (`Area (px)` / `Count`), and the count, mean, and median. The footnote cites CC0 1.0, Caicedo et al. Nature Methods 2019, and BBBC038v1. The story then writes that figure to `demos/bbbc038/out/story_stage1_test.png` and `story_stage1_test.pdf` at 300 dpi and closes it. Those files are gitignored. The 1-by-2 before/after panel stays the current figure, and the standalone histogram stays the only other figure. A review snapshot of the export is in `docs/acceptance/EPIC-1024-v07.png`.

Licence: CC0 1.0. Dataset: [BBBC038v1](https://bbbc.broadinstitute.org/BBBC038).

- J. C. Caicedo et al., Nucleus segmentation across imaging experiments: the 2018 Data Science Bowl, Nature Methods 16:1247–1253, 2019. doi:[10.1038/s41592-019-0612-7](https://doi.org/10.1038/s41592-019-0612-7).
