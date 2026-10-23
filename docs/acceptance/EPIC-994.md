# Acceptance evidence: Epic #994 (V-E1 C-MAPSS FD001 download and readtable)

**Epic:** [#994](https://github.com/superche/openmatlab/issues/994)  
**Milestone:** [C-MAPSS PHM vertical (M14)](https://github.com/superche/openmatlab/milestone/14) · [`docs/milestones/M14-cmapss-vertical.md`](../milestones/M14-cmapss-vertical.md)  
**Design:** [`docs/design/EPIC-994-cmapss-fd001.md`](../design/EPIC-994-cmapss-fd001.md)  
**Captured:** 2026-10-23  
**Functional tip:** `996912c8b48dd6087fa12b92ec61fe5df4b2a94c` (the feature commit on this branch; re-run the commands there or on a descendant)  
**Rule:** Outputs below come from real local commands. None are invented.

## Verdict

**Ready for user acceptance.** M14 criteria V01 and V02 are **met**. Epic #994 stays **open** until the user accepts it.

`cmapss_fetch` downloads `CMAPSSData.zip` from Zenodo (CC BY 4.0, DOI 10.5281/zenodo.15346912), checks the byte size and sha256 in `demos/cmapss/manifest.json`, and extracts the three FD001 text files under `downloads/cmapss/`. `demos/cmapss/load_fd001.m` reads them with `readtable` (space delimiter, no header, PHM08 names). The zip and the text files are not committed.

Citation: A. Saxena, K. Goebel, D. Simon, and N. Eklund, PHM08, 2008.

## Functional demo (real CLI output)

```text
$ openmatlab -e "run('demos/cmapss/story_fd001.m')"
FD001 train height=20631 width=26 unique_units=100 unit1_cycles=192

$ python3 -m openmatlab.libs.cmapss fetch
/workspace/downloads/cmapss/fd001

$ git check-ignore -v downloads/cmapss/CMAPSSData.zip downloads/cmapss/fd001/train_FD001.txt
.gitignore:10:downloads/	downloads/cmapss/CMAPSSData.zip
.gitignore:10:downloads/	downloads/cmapss/fd001/train_FD001.txt

$ git ls-files downloads/cmapss
(no output)

$ python3 -c "import hashlib; from pathlib import Path; p=Path('downloads/cmapss/CMAPSSData.zip'); print(p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())"
12425978 74bef434a34db25c7bf72e668ea4cd52afe5f2cf8e44367c55a82bfd91a5a34f
```

The `downloads/` rule already ignores the cache. `downloads/cmapss/` in `.gitignore` restates the M14 policy. A fresh urllib download (cache zip removed first) produced the same size and sha256.

Public FD001 scale checked by `tests/conformance/test_m14_v01_v02.py`: train 20631×26 and 100 units (unit 1 has 192 cycles), test 13096×26 and 100 units, RUL 100×1.

## Measurable gate: pytest

```text
$ python3 -m pytest tests/unit/test_cmapss_fd001.py tests/bdd/test_cmapss_fd001_bdd.py tests/conformance/test_m14_v01_v02.py --tb=no -o addopts= -q --disable-warnings
8 passed in 0.83s

$ python3 -m pytest -m "unit or bdd" --tb=no -o addopts= -q --disable-warnings
2227 passed, 1 skipped, 37 deselected, 29 warnings in 97.99s (0:01:37)
```

New cases: `tests/unit/test_cmapss_fd001.py` (6), `tests/bdd/test_cmapss_fd001_bdd.py` (1), `tests/conformance/test_m14_v01_v02.py` (1).

**Existing tests changed: none.**

## Feature map

```text
$ openmatlab features | grep cmapss
libs.cmapss_fd001                libs       partial  C-MAPSS FD001 runtime download and readtable load
```

`partial`: this feature is the FD001 fetch and load. V03–V10 are later epics.

## Residuals

No new residual. FD002–FD004 are milestone non-goals. The rest of the `readtable` edge matrix stays on [#721](https://github.com/superche/openmatlab/issues/721).

## Milestone progress (M14)

- Criteria met: **2 / 10** (V01, V02)
- Conformance: V01 and V02 passing. V03–V10 have no scripts yet (epics #995–#999).
- Next: V-E2 #995.

## CI

The required `test` check is the PR's GitHub Actions job. This file does not invent that URL; it is added when the job is green.
