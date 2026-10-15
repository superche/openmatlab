# Acceptance evidence: Epic #622 (packages, import, Static methods, enumerations and introspection)

**Epic:** [#622](https://github.com/superche/openmatlab/issues/622)  
**Feature PR:** [#670](https://github.com/superche/openmatlab/pull/670) (#622)  
**Milestone:** [Object system (M8)](https://github.com/superche/openmatlab/milestone/8) · [`docs/milestones/M8-object-system.md`](../milestones/M8-object-system.md)  
**Design + adversarial review:** [`docs/design/EPIC-622-packages-enums-metaclass.md`](../design/EPIC-622-packages-enums-metaclass.md)  
**Captured:** 2026-10-15 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `1789e47afdd25b7bde226d64df23026d6e9c8960` | Squash merge of feature PR [#670](https://github.com/superche/openmatlab/pull/670) |
| Evidence merge tip | `29b127b17eaf58c4e26fa377ce86fae5f3be6ed6` | Squash merge of [#671](https://github.com/superche/openmatlab/pull/671); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M8 criterion O05 is **met**. Epic #622 stays **open** until the user accepts it.

Covered:
- `+package` functions and classes, nested packages;
- `import pkg.*` and `import pkg.name`;
- `Static` methods called as `Cls.m` / `pkg.Cls.m`;
- enumerations: plain, integer-based (`< int32`), and with properties and a constructor;
- `enumeration()` (listing as a statement, `[m, names]` as outputs), `isenum`, `switch` on members, enumeration arrays;
- `properties`, `methods`, `ismethod`, `isprop`, `fieldnames`, `metaclass`, `?Class`;
- an unresolved package member raises MATLAB's `Unable to resolve the name` error.

O05, O08 and O09 are all met (conformance `m8_o08_enumerations` and `m8_o09_introspection` pass too). O10 still needs O-E6.

No existing test or conformance expected file changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| O-E5 packages/import/Static (O05), enumerations (O08), introspection/metaclass (O09) | #622 | [#670](https://github.com/superche/openmatlab/pull/670) | [job 116494424225](https://github.com/superche/openmatlab/actions/runs/38755989814/job/116494424225) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "addpath('demos/classdef'); shapes.circleArea(2)"
ans =

12.5664
$ openmatlab -e "addpath('demos/classdef'); import shapes.*; circleArea(1)"
ans =

3.1416
$ openmatlab -e "addpath('demos/classdef'); L = [LightDemo.Red LightDemo.Green]"
L =

  1×2 LightDemo enumeration array

    Red      Green
$ openmatlab -e "addpath('demos/classdef'); enumeration LightDemo"

Enumeration members for class 'LightDemo':

    Red
    Amber
    Green
$ openmatlab -e "addpath('demos/classdef'); LightDemo.Green > LightDemo.Amber"
ans =

1
$ openmatlab -e "addpath('demos/classdef'); mc = ?LightDemo; mc.Name"
ans =

LightDemo
$ openmatlab -e "addpath('demos/classdef'); shapes.nope(1)"
error: Unable to resolve the name 'shapes.nope'.
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1458 passed, 2 deselected, 3 xfailed in 15.86s
$ pytest tests/unit/test_classdef_packages_enums.py tests/bdd/test_classdef_packages_enums_bdd.py "tests/conformance/test_m8_conformance.py::test_m8_criterion[O05-m8_o05_static_packages]" --tb=no
9 passed in 0.40s
$ pytest tests/conformance/test_m8_conformance.py --tb=no
10 passed, 1 xfailed in 0.48s
```

New cases: 5 unit tests (`tests/unit/test_classdef_packages_enums.py`), 3 Gherkin scenarios (`features/classdef_packages_enums.feature`), and conformance `m8_o05_static_packages` (11 checks), `m8_o08_enumerations` (14 checks) and `m8_o09_introspection` (18 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F lang.classdef_packages_enums
lang.classdef_packages_enums     lang       done     classdef packages, import, Static methods, enumerations, introspection/metaclass
```

## Residuals (filed)

- [#669](https://github.com/superche/openmatlab/issues/669) (p2): import validation, enum construction by name, metaclass object fidelity (`meta.class`/`meta.package`), nested-package error naming, general object arrays.

## Milestone progress (M8)

- Criteria met: **9 / 10** (O01, O02, O03, O04, O05, O06, O07, O08, O09)
- Conformance scripts passing: **9 / 10** (strict xfail pending: O10)
- Next: O-E6 built-in objects on the class model (#623, completes O10), then O-E7 events/listeners (#624), then M3 E6–E7
