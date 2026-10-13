# Acceptance evidence: Epic #619 (handle classes and inheritance)

**Epic:** [#619](https://github.com/superche/openmatlab/issues/619)  
**Feature PR:** [#637](https://github.com/superche/openmatlab/pull/637) (#619)  
**Milestone:** [Object system (M8)](https://github.com/superche/openmatlab/milestone/8) · [`docs/milestones/M8-object-system.md`](../milestones/M8-object-system.md)  
**Design + adversarial review:** [`docs/design/EPIC-619-handle-inheritance.md`](../design/EPIC-619-handle-inheritance.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `51ee0ed445dc5664eb622761ab1cb4d509f33b8d` | Squash merge of feature PR [#637](https://github.com/superche/openmatlab/pull/637) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M8 criterion O02 is **met**. Epic #619 stays **open** until the user accepts it.

Covered:
- handle classes with reference semantics through variables, struct fields, cells and arguments;
- `==`/`~=` identity;
- `isvalid`/`delete` with a destructor hook and errors on deleted handles;
- inheritance (multilevel, `obj@Super`, `meth@Super`, dynamic dispatch from base methods, implicit superclass constructors, `superclasses`, `isa` through ancestors).

O02 and O03 are both met.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| O-E2 handle classes (O02) and inheritance (O03) | #619 | [#637](https://github.com/superche/openmatlab/pull/637) | [job 115188000151](https://github.com/superche/openmatlab/actions/runs/38365029537/job/115188000151) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "addpath('demos/classdef'); a = CounterDemo; b = a; inc(b, 5); a.n"
ans =

5
$ openmatlab -e "addpath('demos/classdef'); a = CounterDemo; b = a; c = CounterDemo; [a == b, a == c]"
ans =

   1   0
$ openmatlab -e "addpath('demos/classdef'); L = LoggedCounterDemo; L.inc(2); L.inc(); [L.n L.calls]"
ans =

   3   2
$ openmatlab -e "addpath('demos/classdef'); L = LoggedCounterDemo; superclasses(L)"
ans =

{2×1 cell}
  (1,1) = CounterDemo
  (2,1) = handle
$ openmatlab -e "addpath('demos/classdef'); h = CounterDemo; delete(h); isvalid(h)"
ans =

0
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1375 passed, 2 deselected, 13 xfailed in 17.95s
$ pytest tests/unit/test_classdef_handle.py tests/bdd/test_classdef_handle_bdd.py "tests/conformance/test_m8_conformance.py::test_m8_criterion[O02-m8_o02_handle_class]" --tb=no
11 passed in 0.45s
$ pytest tests/conformance/test_m8_conformance.py --tb=no
5 passed, 6 xfailed in 0.51s
```

New cases: 8 unit tests (`tests/unit/test_classdef_handle.py`), 2 Gherkin scenarios (`features/classdef_handle.feature`), and conformance `m8_o02_handle_class` (12 checks) and `m8_o03_inheritance` (14 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F lang.classdef_handle
lang.classdef_handle             lang       done     classdef handle classes and inheritance
```

## Residuals (filed)

- [#636](https://github.com/superche/openmatlab/issues/636) (p2): Copyable copy(), SetGet, multiple-inheritance conflicts, Sealed/Abstract class attributes.
- [#624](https://github.com/superche/openmatlab/issues/624) (O-E7): destructors beyond explicit delete.

## Milestone progress (M8)

- Criteria met: **4 / 10** (O01, O02, O03, O04)
- Conformance scripts passing: **4 / 10** (strict xfail pending: O05, O06, O07, O08, O09, O10)
- Next: O-E3 property validation (#620), interleaved with M3-E1 FFT (#625)
