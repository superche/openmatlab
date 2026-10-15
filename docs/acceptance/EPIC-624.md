# Acceptance evidence: Epic #624 (events, listeners, destructors and objects in MAT files)

**Epic:** [#624](https://github.com/superche/openmatlab/issues/624)  
**Feature PR:** [#678](https://github.com/superche/openmatlab/pull/678) (#624)  
**Milestone:** [Object system (M8)](https://github.com/superche/openmatlab/milestone/8) · [`docs/milestones/M8-object-system.md`](../milestones/M8-object-system.md)  
**Design + adversarial review:** [`docs/design/EPIC-624-events-listeners.md`](../design/EPIC-624-events-listeners.md)  
**Captured:** 2026-10-15 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `d8b3def1c30147f4caa772d5c7cfddc1d658e414` | Squash merge of feature PR [#678](https://github.com/superche/openmatlab/pull/678) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M8 criterion O01 is **met**. Epic #624 stays **open** until the user accepts it.

Covered:
- `events` blocks, `addlistener`/`listener`/`notify` (function and method forms);
- `event.listener` (`Source`, `EventName`, `Callback`, settable `Enabled`, `delete`/`isvalid`);
- `event.EventData` (`Source`, `EventName`);
- `delete(obj)` runs the user destructor and drops the object's listeners;
- `save`/`load` of classdef objects as v5 `mxOBJECT` (class name + properties), with MATLAB's missing-class warning.

O-E7 is p2 and has no exit criterion; M8 remains at **10 / 10**.

No existing test or conformance expected file changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| O-E7 events/listeners, destructors, objects in MAT files | #624 | [#678](https://github.com/superche/openmatlab/pull/678) | [job 116506209065](https://github.com/superche/openmatlab/actions/runs/38759355970/job/116506209065) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "addpath('demos/classdef'); s = SignalDemo; addlistener(s, 'Ping', @(src, e) fprintf('%s from %s\n', e.EventName, class(src))); s.ping()"
Ping from SignalDemo
$ openmatlab -e "addpath('demos/classdef'); s = SignalDemo; lh = addlistener(s, 'Ping', @(src, e) disp('hit')); lh.Enabled = false; s.ping(); lh.Enabled = true; s.ping()"
hit
$ openmatlab -e "addpath('demos/classdef'); s = SignalDemo; delete(s)"
SignalDemo closed
$ openmatlab -e "addpath('demos/classdef'); b = BoxDemo; b.w = 9; f = [tempname '.mat']; save(f, 'b'); clear b; load(f); [b.w isa(b, 'BoxDemo')]"
ans =

   9   1
$ openmatlab -e "addpath('demos/classdef'); try, addlistener(SignalDemo, 'Nope', @(s,e) 1); catch e, disp(e.message); end"
The name 'Nope' is not an accessible event for class 'SignalDemo'.
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1474 passed, 2 deselected, 2 xfailed in 16.22s
$ pytest tests/unit/test_classdef_events.py tests/bdd/test_classdef_events_bdd.py "tests/conformance/test_m8_conformance.py::test_m8_criterion[O01-m8_o01_value_class]" --tb=no
8 passed in 0.40s
$ pytest tests/conformance/test_m8_conformance.py --tb=no
11 passed in 0.55s
```

New cases: 5 unit tests (`tests/unit/test_classdef_events.py`) and 2 Gherkin scenarios (`features/classdef_events.feature`). No conformance criterion (O-E7 is p2).

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F lang.classdef_events
lang.classdef_events             lang       done     classdef events/listeners, handle destructors, objects in MAT files
```

## Residuals (filed)

- [#677](https://github.com/superche/openmatlab/issues/677) (p2): property events (PreSet/PostSet), EventData subclasses, destructor on clear/scope exit, saveobj/loadobj and Transient.

## Milestone progress (M8)

- Criteria met: **10 / 10** (O01–O10)
- Conformance scripts passing: **10 / 10** (strict xfail pending: none)
- Next: M3 E6–E7 (domain toolboxes), then Core backlog #569 / residual #640
