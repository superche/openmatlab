# Acceptance evidence: Epic #618 (classdef core: value classes, constructors, methods)

**Epic:** [#618](https://github.com/superche/openmatlab/issues/618)  
**Feature PR:** [#633](https://github.com/superche/openmatlab/pull/633) (#618)  
**Milestone:** [Object system (M8)](https://github.com/superche/openmatlab/milestone/8) · [`docs/milestones/M8-object-system.md`](../milestones/M8-object-system.md)  
**Design + adversarial review:** [`docs/design/EPIC-618-classdef-core.md`](../design/EPIC-618-classdef-core.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `aa9860f60c8938e9c8a9ff2bd9ee6e6ff12bcc6b` | Squash merge of feature PR [#633](https://github.com/superche/openmatlab/pull/633) |
| Evidence merge tip | `41ec4d6d6263f7a7f7572c35ce150e149e10dbc9` | Squash merge of [#634](https://github.com/superche/openmatlab/pull/634); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M8 criterion O01 is **met**. Epic #618 stays **open** until the user accepts it.

Covered:
- a classdef parser (blocks, attributes, local functions);
- value classes with copy-on-write;
- constructors with nargin and implicit superclass construction;
- methods called as `f(obj)` and `obj.f()`, with multiple outputs;
- property attributes (Constant, Dependent with get/set, SetAccess/Access = private);
- MATLAB error IDs;
- default display.

The core language also gained `...` line continuation and trailing commas in literals. O04 is met as well, because it came out of the same class model.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| O-E1 classdef core (O01; O04 from the same class model) | #618 | [#633](https://github.com/superche/openmatlab/pull/633) | [job 115184723971](https://github.com/superche/openmatlab/actions/runs/38364021790/job/115184723971) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "addpath('demos/classdef'); p = PtDemo(3, 4)"
p =

  PtDemo with properties:

    x: 3
    y: 4
    r: 5
$ openmatlab -e "addpath('demos/classdef'); p = PtDemo(3, 4); q = p; q.x = 10; [p.x q.x]"
ans =

    3   10
$ openmatlab -e "addpath('demos/classdef'); p = shift(PtDemo(1, 1), 2); p.x"
error: Undefined function or variable: shift
$ openmatlab -e "addpath('demos/classdef'); p = PtDemo(3, 4); p.r"
ans =

5
$ openmatlab -e "addpath('demos/classdef'); p = PtDemo; try, p.nope, catch e, disp(e.identifier), end"
MATLAB:noSuchMethodOrField
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1362 passed, 2 deselected, 15 xfailed in 17.52s
$ pytest tests/unit/test_classdef_core.py tests/bdd/test_classdef_core_bdd.py "tests/conformance/test_m8_conformance.py::test_m8_criterion[O01-m8_o01_value_class]" --tb=no
10 passed in 0.46s
$ pytest tests/conformance/test_m8_conformance.py --tb=no
3 passed, 8 xfailed in 0.52s
```

New cases: 7 unit tests (`tests/unit/test_classdef_core.py`), 2 Gherkin scenarios (`features/classdef_core.feature`), and conformance `m8_o01_value_class` (18 checks) and `m8_o04_property_attributes` (12 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F lang.classdef_core
lang.classdef_core               lang       done     classdef value classes, constructors, methods
```

## Residuals (filed)

- [#620](https://github.com/superche/openmatlab/issues/620) (O-E3): property validation enforcement, immutable/Abstract/Hidden.
- [#622](https://github.com/superche/openmatlab/issues/622) (O-E5): object arrays.

## Milestone progress (M8)

- Criteria met: **2 / 10** (O01, O04)
- Conformance scripts passing: **2 / 10** (strict xfail pending: O02, O03, O05, O06, O07, O08, O09, O10)
- Next: O-E2 handle classes and inheritance (#619)
