# Acceptance evidence: Epic #697 (T-E7 timetable)

**Epic:** [#697](https://github.com/superche/openmatlab/issues/697)  
**Feature PR:** [#756](https://github.com/superche/openmatlab/pull/756) (#697, #755)  
**Milestone:** [Tables and data types (M10)](https://github.com/superche/openmatlab/milestone/10) · [`docs/milestones/M10-tables.md`](../milestones/M10-tables.md)  
**Design + adversarial review:** [`docs/design/EPIC-697-timetable.md`](../design/EPIC-697-timetable.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `c3f6a4dbab4362b847aec1ad3349ffb0587ed356` | Squash merge of feature PR [#756](https://github.com/superche/openmatlab/pull/756) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M10 criterion T10 is **met**. Epic #697 stays **open** until the user accepts it.

T10 is met: `timetable` construction and display, time subscripts (datetime, `timerange`, `withtol`), `table2timetable`/`timetable2table`, `retime` and `synchronize` with aggregation and fill methods, and `lag`. Errors are MATLAB-style.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| T10 timetable / timerange / withtol / retime / synchronize / lag | #697 | [#756](https://github.com/superche/openmatlab/pull/756) | [job 116835640322](https://github.com/superche/openmatlab/actions/runs/38858629115/job/116835640322) **success** |
| residual | #755 | [#756](https://github.com/superche/openmatlab/pull/756) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "t = datetime(2020,1,1) + hours(0:5)'; x = (1:6)'; TT = timetable(t, x)"
TT =

  6×1 timetable

             t              x
             _              _

    01-Jan-2020 00:00:00    1
    01-Jan-2020 01:00:00    2
    01-Jan-2020 02:00:00    3
    01-Jan-2020 03:00:00    4
    01-Jan-2020 04:00:00    5
    01-Jan-2020 05:00:00    6
$ openmatlab -e "t = datetime(2020,1,1) + hours(0:5)'; x = (1:6)'; TT = timetable(t, x); retime(TT, 'regular', 'mean', 'TimeStep', hours(2))"
ans =

  3×1 timetable

             t               x
             _               _

    01-Jan-2020 00:00:00    1.5
    01-Jan-2020 02:00:00    3.5
    01-Jan-2020 04:00:00    5.5
$ openmatlab -e "t = datetime(2020,1,1) + hours(0:5)'; x = (1:6)'; TT = timetable(t, x); TT(timerange(datetime(2020,1,1,1,0,0), datetime(2020,1,1,3,0,0)), :)"
ans =

  2×1 timetable

             t              x
             _              _

    01-Jan-2020 01:00:00    2
    01-Jan-2020 02:00:00    3
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1782 passed, 2 deselected in 19.55s
$ pytest tests/unit/test_timetable.py tests/bdd/test_timetable_bdd.py "tests/conformance/test_m10_conformance.py::test_m10_criterion[T10-m10_t10_timetable]" --tb=no
19 passed in 0.43s
$ pytest tests/conformance/test_m10_conformance.py --tb=no
11 passed in 0.41s
```

New cases: `tests/unit/test_timetable.py` (16), `tests/bdd/test_timetable_bdd.py` (2), M10 T10 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F runtime.timetable
runtime.timetable                runtime    done     timetable
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| Calendar retime steps, spline/pchip, EndValues, non-numeric aggregation, NaN duration display, isregular/containsrange, table verbs returning timetables | [#755](https://github.com/superche/openmatlab/issues/755) |

## Milestone progress (M10)

- Criteria met: **10 / 10** (T01, T02, T03, T04, T05, T06, T07, T08, T09, T10)
- Conformance scripts passing: **10 / 10** (strict xfail pending: none)
- Next: M10 exit review.
