# Acceptance evidence: Epic #630 (community.signal plugin breadth)

**Epic:** [#630](https://github.com/superche/openmatlab/issues/630)  
**Feature PR:** [#682](https://github.com/superche/openmatlab/pull/682) (#630)  
**Milestone:** [Domain toolboxes (M3)](https://github.com/superche/openmatlab/milestone/3) · [`docs/milestones/M3-domain-toolboxes.md`](../milestones/M3-domain-toolboxes.md)  
**Design + adversarial review:** [`docs/design/EPIC-630-community-signal.md`](../design/EPIC-630-community-signal.md)  
**Captured:** 2026-10-15 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `8d693b514f43959f5ce6e6afab14753073dafb0c` | Squash merge of feature PR [#682](https://github.com/superche/openmatlab/pull/682) |
| Evidence merge tip | `acf2a4584ee0b41073327e9488b1812f7d1852b9` | Squash merge of [#683](https://github.com/superche/openmatlab/pull/683); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M3 criterion T06 is **met**. Epic #630 stays **open** until the user accepts it.

Covered (community.signal plugin, not core):
- `hann` (symmetric/periodic) and `kaiser` windows;
- `butter` low/high design by the bilinear transform;
- `freqz` (n points, `'whole'`, frequency vector, plot when called with no outputs);
- `filtfilt` zero-phase filtering with Gustafsson initial conditions;
- `which('hann')` resolves to the plugin's `mfiles`.

Core does not import the plugin, and domain gate criteria D01–D04 still pass.

No existing test or conformance expected file changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| M3-E6 community.signal hann/kaiser/butter/freqz/filtfilt (T06) | #630 | [#682](https://github.com/superche/openmatlab/pull/682) | [job 116512598329](https://github.com/superche/openmatlab/actions/runs/38761194848/job/116512598329) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "addpath('demos/plugins/community.signal/mfiles'); which('butter')"
ans =

/workspace/openmatlab/demos/plugins/community.signal/mfiles/butter.m
$ openmatlab -e "addpath('demos/plugins/community.signal/mfiles'); hann(5)'"
ans =

   0.0000   0.5000   1.0000   0.5000   0.0000
$ openmatlab -e "addpath('demos/plugins/community.signal/mfiles'); [b, a] = butter(2, 0.5)"
b =

   0.2929   0.5858   0.2929

a =

    1.0000   -0.0000    0.1716
$ openmatlab -e "addpath('demos/plugins/community.signal/mfiles'); [h, w] = freqz([1 1], 1, 4); [abs(h) w]"
ans =

   2.0000   0.0000
   1.8478   0.7854
   1.4142   1.5708
   0.7654   2.3562
$ openmatlab -e "addpath('demos/plugins/community.signal/mfiles'); filtfilt([0.5 0.5], 1, 1:10)"
ans =

    1    2    3    4    5    6    7    8    9   10
$ openmatlab -e "which('butter')"
ans =
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1481 passed, 2 deselected, 1 xfailed in 15.92s
$ pytest tests/unit/test_community_signal_m3.py tests/bdd/test_community_signal_m3_bdd.py "tests/conformance/test_m3_conformance.py::test_m3_criterion[T06-m3_t06_signal_plugin]" --tb=no
6 passed in 0.44s
$ pytest tests/conformance/test_m3_conformance.py --tb=no
7 passed, 1 xfailed in 0.50s
```

New cases: 3 unit tests (`tests/unit/test_community_signal_m3.py`), 2 Gherkin scenarios (`features/community_signal_m3.feature`), and conformance `m3_t06_signal_plugin` (13 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F plugin.community_signal_m3
plugin.community_signal_m3       plugin     done     community.signal hann/kaiser/butter/freqz/filtfilt (M3-E6)
```

## Residuals (filed)

- [#681](https://github.com/superche/openmatlab/issues/681) (p2): butter bandpass/stop, fir1/cheby/ellip, periodic flag for the other windows, filtfilt edge cases, core empty-range assign.

## Milestone progress (M3)

- Criteria met: **6 / 7** (T01, T02, T03, T04, T05, T06)
- Conformance scripts passing: **6 / 7** (strict xfail pending: T07)
- Next: M3-E7 sparse maturity (#631)
