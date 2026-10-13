# Acceptance evidence — Epic #506 (structs)

**Epic:** [#506 Epic: structs](https://github.com/superche/openmatlab/issues/506)  
**Feature PR:** [#507](https://github.com/superche/openmatlab/pull/507) (also #504 part 1: regexp `'names'` returns a struct)  
**Milestone:** [Octave-breadth language & numerics (M2)](https://github.com/superche/openmatlab/milestone/2) · [`docs/milestones/M2-octave-breadth.md`](../milestones/M2-octave-breadth.md)  
**Design + adversarial review:** [`docs/design/EPIC-506-structs.md`](../design/EPIC-506-structs.md)  
**Captured:** 2026-10-13 ~11:20 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `76923a2c14533af268a8c5d6b54c49278eca2b29` | Squash merge of feature PR [#507](https://github.com/superche/openmatlab/pull/507) |
| Evidence merge tip | _recorded by the after-epic sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M2 criterion C18 is **met**. Epic #506 stays **open** until the user accepts it.

**Side fix found during the review:** `x = []; x(3) = 1` used to give 3x1. It now gives 1x3, as in MATLAB. No existing test asserted the old shape.

## Traceability — Scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| `s.f`, nested/dynamic fields, chained assignment, struct arrays (grow/delete/concat/transpose/for), `struct()`, field functions, cs-lists, display, `isequal`/`size`/`numel`/`isempty` | #506 | [#507](https://github.com/superche/openmatlab/pull/507) | [job 115100393103](https://github.com/superche/openmatlab/actions/runs/38337370191/job/115100393103) **success** |
| regexp `'names'` returns a 1xN struct (0x0 when there is no match) | #504 | [#507](https://github.com/superche/openmatlab/pull/507) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "s.a = 1; s.bcd = 'hi'; s.v = [1 2 3]; s.m = ones(2); s.c = {1, 2}; s.n.x = 1; s"
s =

  struct with fields:

      a: 1
    bcd: 'hi'
      v: [1 2 3]
      m: [2×2 double]
      c: {1×2 cell}
      n: [1×1 struct]

$ openmatlab -e "s = struct('a', {4, 5, 6}), v = [s.a]"
s =

  1×3 struct array with fields:

    a

v =

   4   5   6

$ openmatlab -e "s(3).a = 5; e = isempty(s(1).a), f = fieldnames(s)"
e =

1

f =

{1x1 cell}
  (1,1) = a

$ openmatlab -e "f = 'dyn'; s.(f) = 7; s.dyn"
ans =

7

$ openmatlab -e "s = struct('a', {1, 2}); s.a"
ans =

1

ans =

2

$ openmatlab -e "t = regexp('ab12', '(?<w>[a-z]+)(?<d>\d+)', 'names')"
t =

  struct with fields:

    w: 'ab'
    d: '12'

$ openmatlab -e "[o, p] = orderfields(struct('b', 1, 'a', 2))"
o =

  struct with fields:

    a: 2
    b: 1

p =

   2
   1

$ openmatlab -e "s = struct('a', {1, 2}); s.a = 3"
error: Scalar structure required for this assignment.
$ openmatlab -e "e = struct('a', {})"
e =

  0×0 empty struct array with fields:

    a
```

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
1022 passed, 2 deselected in 3.74s
$ pytest tests/conformance --tb=no
25 passed in 0.46s
$ pytest tests/unit/test_structs.py tests/bdd/test_structs_bdd.py "tests/conformance/test_m2_conformance.py::test_m2_criterion[C18-c18_structs]"
17 passed in 0.90s
```

New cases: 13 unit (`tests/unit/test_structs.py`), 3 Gherkin scenarios
(`features/structs.feature`), and conformance `c18_structs`.

**Existing tests changed: one.** In `tests/unit/test_string_residuals.py::test_regexp_outputs`, the `'names'`
assertion expected the 2xN `{name; value}` cell from before structs existed. It now asserts a struct
with fields `key`/`val` and values `k`/`v`, which is what #504 asked for. The other assertions in that test are unchanged.

## Feature map (epic-related)

```text
$ openmatlab features | rg structs
runtime.structs                  runtime    done     structs and struct arrays
```

## Residuals (filed)

- [#508](https://github.com/superche/openmatlab/issues/508): `[a,b] = s.f` / `deal`, `struct2cell`/`cell2struct`/`structfun`/`arrayfun`, `disp`, `isrow` and friends, N-D struct arrays, field-summary short-g formatting.
- [#504](https://github.com/superche/openmatlab/issues/504): the `missing` class (the `'names'` part is done).

## Milestone progress (M2)

- Criteria met: **18 / 18** (C18 added at p2 and met by this epic)
- Conformance scripts passing: **18 / 18** (xfail pending: none)
- Remaining gaps (all p2): #498, #501, #503, #504 (missing class), #505, #508
