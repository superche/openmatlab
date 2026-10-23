# C-MAPSS FD001 (M14 V-E1)

Runtime download of NASA C-MAPSS from Zenodo and a `readtable` load of FD001.
The zip and the extracted text are cached under `downloads/cmapss/` and are
not part of the repository.

Citation: A. Saxena, K. Goebel, D. Simon, and N. Eklund, "Damage Propagation
Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08, 2008.
Data: DOI 10.5281/zenodo.15346912 (CC BY 4.0).

From the repository root:

```text
openmatlab -e "run('demos/cmapss/story_fd001.m')"
```

`load_fd001('train'|'test'|'rul')` is the script a MATLAB user would write:
space delimiter, no header, PHM08 names (`unit`, `cycle`, three settings,
21 sensors). `python -m openmatlab.libs.cmapss fetch` only fills the cache.

`story_fd001.m` then keeps unit 1, drops sensor columns whose sample standard
deviation is at most `1e-6`, and plots that unit's busiest remaining channel
with `smoothdata(...,'movmean',15)` and `smoothdata(...,'gaussian',15)` on the
same axes (M14 V03).
