# Acceptance evidence: Epic #539 (containers.Map and date/time basics)

**Epic:** [#539](https://github.com/superche/openmatlab/issues/539)  
**Feature PR:** [#603](https://github.com/superche/openmatlab/pull/603) (#561, #562)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-539-map-datetime.md`](../design/EPIC-539-map-datetime.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `a2396d4a908cb68f52cbb5ab71f74f71d8453eaa` | Squash merge of feature PR [#603](https://github.com/superche/openmatlab/pull/603) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M7 criterion C10 is **met**. Epic #539 stays **open** until the user accepts it.

Covered:
- a generic object protocol in the evaluator (operators, indexing, indexed assignment, properties/methods, display);
- `containers.Map` with handle semantics, sorted keys, typed keys/values and MATLAB errors;
- `datetime`/`duration` value types with MATLAB arithmetic, rollover and comparison;
- unit conversions (`days`/`hours`/`minutes`/`seconds`/`years`);
- `datenum`/`datestr`/`weekday`/`clock`/`now`/`etime`.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| containers.Map (handle semantics, KeyType/ValueType, keys/values/isKey/remove/Count) | #561 | [#603](https://github.com/superche/openmatlab/pull/603) | [job 115161482421](https://github.com/superche/openmatlab/actions/runs/38356800772/job/115161482421) **success** |
| datetime/duration basics: datetime, year/month/day, days/seconds/minutes, datenum/datestr, clock, weekday | #562 | [#603](https://github.com/superche/openmatlab/pull/603) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "m = containers.Map(); m('b') = 2; m('a') = 1; k = keys(m), n = m.Count"
k =

{1×2 cell}
  (1,1) = a
  (1,2) = b

n =

2
$ openmatlab -e "m = containers.Map(); m2 = m; m2('x') = 1; n = m.Count"
n =

1
$ openmatlab -e "d = datetime(2020, 1, 31) + days(1), t = datetime(2020, 3, 1) - datetime(2020, 2, 1)"
d =

   01-Feb-2020

t =

   696:00:00
$ openmatlab -e "dm = minutes(seconds(90)), w = weekday(datenum(2020, 1, 1))"
dm =

1.5000

w =

4
$ openmatlab -e "s = datestr(datenum(2020, 1, 2, 13, 5, 0)), dn = datenum(2020, 1, 1)"
s =

02-Jan-2020 13:05:00

dn =

737791
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1319 passed, 2 deselected in 17.03s
$ pytest tests/unit/test_map_datetime.py tests/bdd/test_map_datetime_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C10-m7_c10_map_datetime]" --tb=no
13 passed in 0.43s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
11 passed in 1.38s
```

New cases: 9 unit tests (`tests/unit/test_map_datetime.py`), 3 Gherkin scenarios (`features/map_datetime.feature`), and conformance `m7_c10_map_datetime` (23 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.map_datetime
libs.map_datetime                libs       done     containers.Map and date/time basics
```

## Residuals (filed)

- [#602](https://github.com/superche/openmatlab/issues/602) (p2): time zones, InputFormat, calendarDuration, NaT, datetime concatenation, objects in MAT files.

## Milestone progress (M7)

- Criteria met: **10 / 10** (C01–C10)
- Conformance scripts passing: **10 / 10** (strict xfail pending: none)
- Next: M7 close-readiness review
