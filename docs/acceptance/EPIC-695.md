# Acceptance evidence: Epic #695 (T-E5 datetime/duration array completion)

**Epic:** [#695](https://github.com/superche/openmatlab/issues/695)  
**Feature PR:** [#734](https://github.com/superche/openmatlab/pull/734) (#695, #733)  
**Milestone:** [Tables and data types (M10)](https://github.com/superche/openmatlab/milestone/10) · [`docs/milestones/M10-tables.md`](../milestones/M10-tables.md)  
**Design + adversarial review:** [`docs/design/EPIC-695-datetime-arrays.md`](../design/EPIC-695-datetime-arrays.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `448928c17d8ec91b3f05a65e7ada5dd1081ff554` | Squash merge of feature PR [#734](https://github.com/superche/openmatlab/pull/734) |
| Evidence merge tip | `a2ba9ff1868c1b45f7cfa5fa38d382ffa5a9be7d` | Squash merge of [#735](https://github.com/superche/openmatlab/pull/735); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M10 criterion T09 is **met**. Epic #695 stays **open** until the user accepts it.

T09 is met by this epic (time zones stay out of scope). The datetime subset of #602 and the datetime part of #673 are absorbed by reference; those issues stay where they are, untouched.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| T09 datetime arrays, NaT, InputFormat, calendarDuration, between, dateshift | #695 | [#734](https://github.com/superche/openmatlab/pull/734) | [job 116817449529](https://github.com/superche/openmatlab/actions/runs/38852769874/job/116817449529) **success** |
| residual | #733 | [#734](https://github.com/superche/openmatlab/pull/734) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "t = datetime(2020,1,1) + days(0:2)'"
t =

   01-Jan-2020
   02-Jan-2020
   03-Jan-2020
$ openmatlab -e "m = datetime(2020,1,31) + calmonths(1)"
m =

   29-Feb-2020
$ openmatlab -e "b = between(datetime(2020,1,15), datetime(2021,3,20))"
b =

   1y 2mo 5d
$ openmatlab -e "x = datetime(2023,1,1); x.Month = 14"
x =

   01-Feb-2024
$ openmatlab -e "d = datetime('15/03/2021', 'InputFormat', 'dd/MM/yyyy')"
d =

   15/03/2021
$ openmatlab -e "isnat([datetime(2020,1,1) NaT])"
ans =

   0   1
$ openmatlab -e "dateshift(datetime(2021,2,10), 'end', 'month')"
ans =

   28-Feb-2021
$ openmatlab -e "calmonths(1) < calmonths(2)"
error: Relational comparisons are not defined for calendar durations, because their lengths vary.
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1669 passed, 2 deselected, 7 xfailed in 18.69s
$ pytest tests/unit/test_datetime_arrays.py tests/bdd/test_datetime_arrays_bdd.py "tests/conformance/test_m10_conformance.py::test_m10_criterion[T09-m10_t09_datetime_arrays]" --tb=no
38 passed in 0.43s
$ pytest tests/conformance/test_m10_conformance.py --tb=no
6 passed, 5 xfailed in 0.41s
```

New cases: `tests/unit/test_datetime_arrays.py` (33), `tests/bdd/test_datetime_arrays_bdd.py` (4), M10 T09 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.datetime_arrays
libs.datetime_arrays             libs       done     datetime/duration arrays, NaT, InputFormat, calendarDuration, between, dateshift
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| dateshift 'end' for day/time units and dayofweek, time zones, calendarDuration Format, ConvertFrom, caldiff, duration display precision | [#733](https://github.com/superche/openmatlab/issues/733) |

## Milestone progress (M10)

- Criteria met: **5 / 10** (T01, T02, T04, T08, T09)
- Conformance scripts passing: **5 / 10** (strict xfail pending: T03, T05, T06, T07, T10)
- Next: T-E3 #693 (table utilities, sorting and sets), interleaved with D-E5 #702.
