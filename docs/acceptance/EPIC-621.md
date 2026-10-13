# Acceptance evidence: Epic #621 (operators, indexing overloads and display)

**Epic:** [#621](https://github.com/superche/openmatlab/issues/621)  
**Feature PR:** [#654](https://github.com/superche/openmatlab/pull/654) (#621)  
**Milestone:** [Object system (M8)](https://github.com/superche/openmatlab/milestone/8) · [`docs/milestones/M8-object-system.md`](../milestones/M8-object-system.md)  
**Design + adversarial review:** [`docs/design/EPIC-621-operators-subsref.md`](../design/EPIC-621-operators-subsref.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `bef4dc8521de54e1e3bdc50e2371f636fced3f30` | Squash merge of feature PR [#654](https://github.com/superche/openmatlab/pull/654) |
| Evidence merge tip | `bcd8b00925f2adab38098766c09c637c36f14508` | Squash merge of [#655](https://github.com/superche/openmatlab/pull/655); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M8 criterion O06 is **met**. Epic #621 stays **open** until the user accepts it.

Covered:
- binary operator overloads with either operand an object;
- unary operators (`uminus`/`uplus`/`not`) and `transpose`/`ctranspose`;
- `horzcat`/`vertcat` in `[...]`;
- `@Class.staticMethod` handles;
- `subsref`/`subsasgn` overloads with substruct `s`, multi-level indexing, a `builtin('subsref'|'subsasgn')` fallback, and no recursion inside class methods;
- `builtin()`, `substruct`;
- `disp`/`display` overloads in variable display.

O06 and O07 are both met (conformance `m8_o07_subsref_subsasgn` passes too). O10 still needs O-E6 for dot notation on built-in objects.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| O-E4 operators (O06), subsref/subsasgn (O07), display overloads (O10 part) | #621 | [#654](https://github.com/superche/openmatlab/pull/654) | [job 115208062274](https://github.com/superche/openmatlab/actions/runs/38371117107/job/115208062274) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "addpath('demos/classdef'); a = MoneyDemo(250); b = a + 199"
b =

$4.49
$ openmatlab -e "addpath('demos/classdef'); a = MoneyDemo(250); [a a 5]"
ans =

$5.05
$ openmatlab -e "addpath('demos/classdef'); MoneyDemo(100) * 3 < 400"
ans =

1
$ openmatlab -e "addpath('demos/classdef'); t = TallyDemo; t{'x'} = 3; [t{'x'} t{'y'}]"
ans =

   3   0
$ openmatlab -e "s.a = [1 2 3]; subsref(s, substruct('.', 'a', '()', {2}))"
ans =

2
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1423 passed, 2 deselected, 9 xfailed in 21.30s
$ pytest tests/unit/test_classdef_operators.py tests/bdd/test_classdef_operators_bdd.py "tests/conformance/test_m8_conformance.py::test_m8_criterion[O06-m8_o06_operator_overloading]" --tb=no
10 passed in 0.51s
$ pytest tests/conformance/test_m8_conformance.py --tb=no
7 passed, 4 xfailed in 0.60s
```

New cases: 7 unit tests (`tests/unit/test_classdef_operators.py`), 2 Gherkin scenarios (`features/classdef_operators.feature`), and conformance `m8_o06_operator_overloading` (14 checks) and `m8_o07_subsref_subsasgn` (8 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F lang.classdef_operators
lang.classdef_operators          lang       done     classdef operator/concatenation/subsref/subsasgn/display overloads
```

## Residuals (filed)

- [#653](https://github.com/superche/openmatlab/issues/653) (p2): InferiorClasses precedence, numel/size overloads, objects shown inside cells, object arrays without concatenation overloads.

## Milestone progress (M8)

- Criteria met: **6 / 10** (O01, O02, O03, O04, O06, O07)
- Conformance scripts passing: **6 / 10** (strict xfail pending: O05, O08, O09, O10)
- Next: M3-E3 ODE/quadrature/optimisation (#627), M3-E4 (#628), M3-E5 (#629), then O-E5 (#622)
