# Acceptance evidence: Epic #610 (Caller/base workspaces and help browsing (evalin/assignin/doc/lookfor/what))

**Epic:** [#610](https://github.com/superche/openmatlab/issues/610)  
**Feature PR:** [#612](https://github.com/superche/openmatlab/pull/612) (#608)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-610-frames-help.md`](../design/EPIC-610-frames-help.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `e873262bc32325cdc654b08015980962ce66e0b1` | Squash merge of feature PR [#612](https://github.com/superche/openmatlab/pull/612) |
| Evidence merge tip | `652c63a56f2ca7b3b292fc6d34eda5d490497311` | Squash merge of [#613](https://github.com/superche/openmatlab/pull/613); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M7 criterion C11 is **met**. Epic #610 stays **open** until the user accepts it.

Covered:
- a call-frame stack that unwinds on error;
- `evalin`/`assignin` in `'base'`/`'caller'` (nested, anonymous-function and cellfun callers, catch string, MATLAB error IDs);
- `doc` prints help text;
- `lookfor` searches H1 lines (supports `-all`);
- `what` gives a listing or a struct.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| evalin, doc/lookfor/what missing (GAP p0 leftovers) | #608 | [#612](https://github.com/superche/openmatlab/pull/612) | [job 115169711147](https://github.com/superche/openmatlab/actions/runs/38359387256/job/115169711147) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "evalin('base', 'x0 = 41;'); y = evalin('base', 'x0 + 1')"
y =

42
$ openmatlab -e "assignin('base', 'q', 7); q"
q =

7
$ openmatlab -e "v = evalin('base', 'undefined_zz', '-1')"
v =

-1
$ openmatlab -e "f = @() evalin('caller', '3'); r = f()"
r =

3
$ openmatlab -e "w = what(tempdir); isstruct(w)"
ans =

1
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1340 passed, 2 deselected in 18.14s
$ pytest tests/unit/test_frames_help.py tests/bdd/test_frames_help_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C11-m7_c11_frames_help]" --tb=no
10 passed in 0.41s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
12 passed in 1.39s
```

New cases: 7 unit tests (`tests/unit/test_frames_help.py`), Gherkin scenarios (`features/frames_help.feature`), and conformance `m7_c11_frames_help` (18 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.frames_help
libs.frames_help                 libs       done     caller/base workspaces and help browsing
```

## Residuals (filed)

- [#611](https://github.com/superche/openmatlab/issues/611) (p2): frames for GUI callbacks and nested sessions, `dbstack`/`inputname`, an HTML doc browser, builtin H1 text for `lookfor`, and `what` listing package/class contents.

## Milestone progress (M7)

- Criteria met: **11 / 11** (C01–C11)
- Conformance scripts passing: **11 / 11** (strict xfail pending: none)
- Next: M7 close-readiness review (rerun); M7 to be closed by user
