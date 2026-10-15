# Acceptance evidence: Epic #623 (built-in objects on the class model)

**Epic:** [#623](https://github.com/superche/openmatlab/issues/623)  
**Feature PR:** [#674](https://github.com/superche/openmatlab/pull/674) (#623)  
**Milestone:** [Object system (M8)](https://github.com/superche/openmatlab/milestone/8) · [`docs/milestones/M8-object-system.md`](../milestones/M8-object-system.md)  
**Design + adversarial review:** [`docs/design/EPIC-623-builtin-objects.md`](../design/EPIC-623-builtin-objects.md)  
**Captured:** 2026-10-15 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `1de36288f2e97424bfaa40aa70869f3f2f7d3d41` | Squash merge of feature PR [#674](https://github.com/superche/openmatlab/pull/674) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M8 criterion O10 is **met**. Epic #623 stays **open** until the user accepts it.

Covered:
- scalar graphics handles support dot notation: `h.Prop` reads, `h.Prop = v` writes (with `set`'s validation and read-only checks), and `ax.XLim(2)`;
- handle semantics: copies of a handle change the same object;
- `isvalid(h)` is false after `close`/`delete`, `h.Prop` on a deleted object raises `Invalid or deleted object.`, and `isobject(h)` is true;
- handles stay numeric ids, so `get`/`set`/`==`/`ishandle` are unchanged;
- datetime `.Year`/`.Month`/`.Day` and `containers.Map` `.Count` work through the object property path.

With O-E4's display overloads, O10 is now met, which puts M8 at 10 / 10.

No existing test or conformance expected file changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| O-E6 graphics h.Prop / isvalid / isobject, datetime dot access (O10) | #623 | [#674](https://github.com/superche/openmatlab/pull/674) | [job 116500323157](https://github.com/superche/openmatlab/actions/runs/38757678422/job/116500323157) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "f = figure('Visible','off'); h = plot(1:3); h.LineWidth = 3; get(h, 'LineWidth')"
ans =

3
$ openmatlab -e "f = figure('Visible','off'); ax = gca; ax.XLim = [0 5]; ax.XLim(2)"
ans =

5
$ openmatlab -e "f = figure('Visible','off'); h = plot(1:3); k = h; k.LineWidth = 5; h.LineWidth"
ans =

5
$ openmatlab -e "f = figure('Visible','off'); h = plot(1:3); close(f); [isvalid(h) isobject(h)]"
ans =

   0   1
$ openmatlab -e "f = figure('Visible','off'); h = plot(1:3); close(f); h.LineWidth"
error: Invalid or deleted object.
$ openmatlab -e "dt = datetime(2020, 5, 6); [dt.Year dt.Month dt.Day]"
ans =

   2020      5      6
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1466 passed, 2 deselected, 2 xfailed in 17.01s
$ pytest tests/unit/test_graphics_dot_objects.py tests/bdd/test_graphics_dot_objects_bdd.py "tests/conformance/test_m8_conformance.py::test_m8_criterion[O10-m8_o10_display_dot_objects]" --tb=no
7 passed in 0.96s
$ pytest tests/conformance/test_m8_conformance.py --tb=no
11 passed in 0.57s
```

New cases: 4 unit tests (`tests/unit/test_graphics_dot_objects.py`), 2 Gherkin scenarios (`features/graphics_dot_objects.feature`), and conformance `m8_o10_display_dot_objects` (11 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F lang.builtin_dot_objects
lang.builtin_dot_objects         lang       done     dot notation on built-in objects (graphics h.Prop get/set, datetime/Map properties)
```

## Residuals (filed)

- [#673](https://github.com/superche/openmatlab/issues/673) (p2): MATLAB class names and display for graphics objects, `h(k).Prop` on handle arrays, datetime component assignment. Remaining non-object graphics/datetime items stay in #593/#602.

## Milestone progress (M8)

- Criteria met: **10 / 10** (O01–O10)
- Conformance scripts passing: **10 / 10** (strict xfail pending: none)
- Next: O-E7 events/listeners, destructors, objects in MAT files (#624), then M3 E6–E7
