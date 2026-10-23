# Epic #1020 (I-E1): BBBC038 stage1_test download and PNG imread

Milestone: [M16 BBBC038 nuclei image vertical](../milestones/M16-bbbc038-vertical.md), criteria V01 and V02.

## Problem

A nuclei script starts by downloading Broad BBBC038 `stage1_test.zip` and reading one field of view. The bytes must not enter the repository. OpenMATLAB has no `imread`, so this epic adds a PNG reader sufficient for these FOVs.

## Design

- **Manifest.** `demos/bbbc038/manifest.json` is metadata only: the Broad URL, CC0 1.0, doi:10.1038/s41592-019-0612-7, the zip size 9545388, the zip sha256, and one FOV member (size, sha256, 256 by 256, 8-bit color type 6). No zip and no PNG bytes.
- **Fetch.** `libs/bbbc038.py` (`python -m openmatlab.libs.bbbc038 fetch`, or MATLAB `bbbc038_fetch`) writes `downloads/bbbc038/stage1_test.zip`. The file is checked against the manifest size and sha256. A match is not downloaded again. When the response has a Content-Length header, that header must be 9545388 before the body is kept. `$OPENMATLAB_BBBC038_CACHE` overrides the cache root.
- **One FOV.** The manifest names one zip member. `extract_fov` reads that member's bytes and writes `downloads/bbbc038/fov/<basename>.png`. The member string is not a filesystem path. A segment of `..`, an empty segment, a backslash, or a leading `/` is rejected before the zip is opened for that name.
- **imread.** Non-interlaced PNG, bit depth 8 or 16, color types 0 (gray), 2 (RGB), 4 (gray + alpha), and 6 (RGB + alpha). Filters None, Sub, Up, Average, and Paeth. `A` is gray `(H, W)` or RGB `(H, W, 3)`. Alpha is the third output, not a fourth page of `A`. The colormap output is empty. Each side is limited to 4096 pixels, and inflate stops at the IHDR byte count. Indexed color, Adam7, and bit depths below 8 raise.
- **Demo FOV.** The lexicographically first stage1_test image. On disk it is 8-bit RGBA, 256 by 256. `imread` returns uint8 RGB. Pillow's decode of the same bytes matches, including alpha 255. MATLAB `I(1,1,:)` is `[3 3 3]`. `I(129,129,:)` is `[6 6 6]`.
- **Story.** `demos/bbbc038/load_fov.m` calls `bbbc038_fetch` then `imread`. `demos/bbbc038/story_stage1_test.m` prints the zip path and byte size (V01) and the image path, size, and class (V02).

Citation recorded in the module, the loader, and the demo: Caicedo et al., Nature Methods 2019; BBBC038v1; CC0 1.0.

## Non-goals

`stage1_train`. More than the one demo FOV. JPEG, TIFF, GIF, indexed PNG, Adam7, bit depth below 8, and the `imread` option matrix. `imbinarize`, `bwareaopen`, `regionprops`, the lab figure, and export (I-E2…I-E6, epics #1021–#1025).

## Adversarial review

| Attack | Result |
|---|---|
| Zip of the wrong size or sha256 | `RuntimeError` from `verify_cached`; the bad file is deleted and the download retried |
| Content-Length header other than 9545388 | `RuntimeError` before the partial file is kept |
| Download error | Three attempts, then `bbbc038_fetch: could not download stage1_test.zip` |
| Zip member `../evil.png` | Rejected as not a safe zip path. Nothing is written outside the cache |
| Not a PNG, bad CRC, interlaced, indexed, bit depth 4, side 4097 | `RuntimeError` from `decode_png` |
| RGBA file | `A` is RGB. Alpha is only the third output |
| `imread` with a format argument | `MATLAB:TooManyInputs` |
| `bbbc038_fetch` with an argument | `MATLAB:TooManyInputs` before any download |
| Missing file | `OpenMATLAB:imread:FileNotFound` |
| Cache path | `git check-ignore` reports `downloads/`. `downloads/bbbc038/` restates the M16 policy. `git ls-files` does not list the zip or the PNG |
| Existing tests | Not modified |
