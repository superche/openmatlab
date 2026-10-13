# Acceptance evidence: Epic #620 (property attributes and validation)

**Epic:** [#620](https://github.com/superche/openmatlab/issues/620)  
**Feature PR:** [#646](https://github.com/superche/openmatlab/pull/646) (#620)  
**Milestone:** [Object system (M8)](https://github.com/superche/openmatlab/milestone/8) · [`docs/milestones/M8-object-system.md`](../milestones/M8-object-system.md)  
**Design + adversarial review:** [`docs/design/EPIC-620-property-validation.md`](../design/EPIC-620-property-validation.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `ce3cc59d869bf7e4150c226d04ae4b4318626467` | Squash merge of feature PR [#646](https://github.com/superche/openmatlab/pull/646) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M8 criterion O04 is **met**. Epic #620 stays **open** until the user accepts it.

O04 was already met through the O-E1 class model (Constant, Dependent with get./set., access attributes). This epic adds:
- property validation `(dims) Class {validators}`, with MATLAB conversion, vector reshape and scalar expansion, run before set methods and on defaults;
- 21 `mustBe*` validators with MATLAB identifiers;
- Abstract classes, methods and properties checked along the MRO;
- immutable and Hidden, now covered by tests.

O04 stays met.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| O-E3 property attributes and validation (O04) | #620 | [#646](https://github.com/superche/openmatlab/pull/646) | [job 115198943913](https://github.com/superche/openmatlab/actions/runs/38368379577/job/115198943913) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "addpath('demos/classdef'); r = RectDemo(2, 3); area(r)"
ans =

6
$ openmatlab -e "addpath('demos/classdef'); r = RectDemo; r.w = '3'; r.w"
ans =

51
$ openmatlab -e "addpath('demos/classdef'); r = RectDemo; try, r.w = -2; catch e, disp(e.message), end"
Error setting property 'w' of class 'RectDemo'. Value must be positive.
$ openmatlab -e "addpath('demos/classdef'); try, s = ShapeDemo; catch e, disp(e.identifier), end"
MATLAB:class:abstract
$ openmatlab -e "mustBeInRange(0.5, 0, 1); disp('in range')"
in range
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1400 passed, 2 deselected, 12 xfailed in 18.34s
$ pytest tests/unit/test_classdef_validation.py tests/bdd/test_classdef_validation_bdd.py "tests/conformance/test_m8_conformance.py::test_m8_criterion[O04-m8_o04_property_attributes]" --tb=no
10 passed in 0.58s
$ pytest tests/conformance/test_m8_conformance.py --tb=no
5 passed, 6 xfailed in 0.54s
```

New cases: 7 unit tests (`tests/unit/test_classdef_validation.py`) and 2 Gherkin scenarios (`features/classdef_validation.feature`). Conformance `m8_o04_property_attributes` stays met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F lang.classdef_validation
lang.classdef_validation         lang       done     classdef property validation, Abstract classes, immutable, Hidden
```

## Residuals (filed)

- [#645](https://github.com/superche/openmatlab/issues/645) (p2): function `arguments` blocks, more mustBe* validators, user-class conversion, and the wording of the immutable error.

## Milestone progress (M8)

- Criteria met: **4 / 10** (O01, O02, O03, O04)
- Conformance scripts passing: **4 / 10** (strict xfail pending: O05, O06, O07, O08, O09, O10)
- Next: M3-E2 polynomials/interpolation (#626), then O-E4 (#621)
