# Acceptance evidence — Epic #457 (integer classes, string class, char indexing)

**Epic:** [#457 Epic: integer classes, string class, char indexing](https://github.com/superche/openmatlab/issues/457)  
**Scope issues (closed by PR #458):** [#72](https://github.com/superche/openmatlab/issues/72) · [#78](https://github.com/superche/openmatlab/issues/78) · [#183](https://github.com/superche/openmatlab/issues/183) · char indexing (residual of #427)  
**Milestone:** [Octave-breadth language & numerics (M2)](https://github.com/superche/openmatlab/milestone/2) · [`docs/milestones/M2-octave-breadth.md`](../milestones/M2-octave-breadth.md)  
**Design + adversarial review:** [`docs/design/EPIC-457-int-string-classes.md`](../design/EPIC-457-int-string-classes.md)  
**Captured:** 2026-10-12 ~22:40 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `b80becaa4cdb8f9803f1319ee6a36a59f355c70e` | Squash merge of [#465](https://github.com/superche/openmatlab/pull/465), after feature PR [#458](https://github.com/superche/openmatlab/pull/458) (`2957f73`) |
| Evidence merge tip | `4019634aa7350ec0832374314d0d892901d756fb` | Squash merge of [#466](https://github.com/superche/openmatlab/pull/466); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** #72, #78 and #183 are closed. M2 criterion C14 is **met**. The epic issue #457 stays **open** until the user accepts it.

## Traceability — Issues → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| int8…uint64 casts, arithmetic, class propagation, predicates, display | #72 | [#458](https://github.com/superche/openmatlab/pull/458) | [job 114860824894](https://github.com/superche/openmatlab/actions/runs/38263823139/job/114860824894) **success** |
| string scalars | #78 | #458 | same |
| `zeros(...,'cls')`, `'like', A` | #183 | #458 | same |
| char indexing / assign / delete / transpose | (#427 residual) | #458 | same |
| backend errors shown as `error: …` (not tracebacks), found during acceptance | — | [#465](https://github.com/superche/openmatlab/pull/465) | [job 114861928703](https://github.com/superche/openmatlab/actions/runs/38264151858/job/114861928703) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "a = uint8(250) + 10, b = int8([2.5 -2.5 200]), c = class(b)"
a =

255

b =

    3   -3  127

c =

int8

$ openmatlab -e "e = int8(1) + int16(1)"
error: Integers can only be combined with integers of the same class, or scalar doubles.
$ openmatlab -e "z = ones(1, 3, 'like', int16(1)), k = class(z)"
z =

  1  1  1

k =

int16

$ openmatlab -e 's = "ab" + "cd", c = class(s), n = strlength(s)'
s =

"abcd"

c =

string

n =

4

$ openmatlab -e "w = 'hello'; w(1) = 'J', r = w(end:-1:1)"
w =

Jello

r =

olleJ

$ openmatlab -e "p = 'a' + 'b'"
p =

195
```

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
733 passed, 2 deselected in 3.05s
$ pytest tests/conformance --tb=no
21 passed in 0.45s
$ pytest tests/unit/test_int_string_classes.py tests/bdd/test_int_string_classes_bdd.py "tests/conformance/test_m2_conformance.py::test_m2_criterion[C14-c14_int_string_classes]"
39 passed in 0.46s
```

New cases: 34 unit (`tests/unit/test_int_string_classes.py`), 4 Gherkin scenarios
(`features/int_string_classes.feature`), and conformance `c14_int_string_classes`.

**Existing tests changed: none.**

**User-visible behaviour change:** `'a' + 'b'` is now numeric `195`, as in MATLAB. Before, it was an undocumented concatenation shortcut that no test relied on. String concatenation is `"a" + "b"`.

## Feature map (epic-related)

```text
$ openmatlab features | rg "int_classes|string_class|char_value"
numerics.int_classes             numerics   partial  integer classes int8..uint64 + class / 'like' constructor args
runtime.string_class             runtime    partial  string scalars (double-quoted literals)
runtime.char_value               runtime    done     CharValue carrier for ' and \" literals
```

The new features are `partial` because of the residuals below.

## Milestone progress (M2)

- Criteria met: **14 / 14** (C14 added at p2 and met by this epic)
- Conformance scripts passing: **14 / 14** (xfail pending: none)
- Remaining gaps (priority order): p2 residuals only. N-D: #442–#446; complex: #451–#454; int/string: #459–#464

## Residuals (filed, same milestone)

| Issue | Residual |
|-------|----------|
| [#459](https://github.com/superche/openmatlab/issues/459) | string arrays |
| [#460](https://github.com/superche/openmatlab/issues/460) | string methods |
| [#461](https://github.com/superche/openmatlab/issues/461) | `single` class |
| [#462](https://github.com/superche/openmatlab/issues/462) | `idivide` / bit ops |
| [#463](https://github.com/superche/openmatlab/issues/463) | exact int64 arithmetic beyond 2^53 |
| [#464](https://github.com/superche/openmatlab/issues/464) | `[1x2 int8]` summaries in cell display |
