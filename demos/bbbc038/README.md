# BBBC038 stage1_test

Runtime download of one Broad BBBC038v1 test zip. The zip and the extracted FOV PNG are cached under `downloads/bbbc038/` and are not part of this repository.

```bash
openmatlab -e "run('demos/bbbc038/story_stage1_test.m')"
```

The story checks the zip size (9545388 bytes) and reads one field of view with `imread`. That PNG is 8-bit RGBA on disk. `imread` returns a uint8 RGB array, 256 by 256 by 3.

It then segments that FOV with global Otsu (`graythresh` / `imbinarize`) and `bwareaopen` at `P = 50` (8-connected). On this FOV the component areas are 1, 24, 117, 143, 152, 154, 193, and 219, so 50 drops the two small objects and keeps the rest. A 1-by-2 `tiledlayout` shows the raw FOV and the mask. The level on this FOV is 22/255. Foreground pixels go from 1003 to 978.

Licence: CC0 1.0. Dataset: [BBBC038v1](https://bbbc.broadinstitute.org/BBBC038).

- J. C. Caicedo et al., Nucleus segmentation across imaging experiments: the 2018 Data Science Bowl, Nature Methods 16:1247–1253, 2019. doi:[10.1038/s41592-019-0612-7](https://doi.org/10.1038/s41592-019-0612-7).
