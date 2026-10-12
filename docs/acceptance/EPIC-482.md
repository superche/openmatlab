# Acceptance evidence — Epic #482 (string arrays and string methods)

**Epic:** [#482 Epic: string arrays and string methods](https://github.com/superche/openmatlab/issues/482)  
**Scope issues (closed by PR #484):** [#459](https://github.com/superche/openmatlab/issues/459) · [#460](https://github.com/superche/openmatlab/issues/460)  
**Milestone:** [Octave-breadth language & numerics (M2)](https://github.com/superche/openmatlab/milestone/2) · [`docs/milestones/M2-octave-breadth.md`](../milestones/M2-octave-breadth.md)  
**Design + adversarial review:** [`docs/design/EPIC-482-string-arrays.md`](../design/EPIC-482-string-arrays.md)  
**Captured:** 2026-10-12 ~23:18 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `26a9c10974bbbf76e72f1219c98beb5dfcd0c553` | Squash merge of feature PR [#484](https://github.com/superche/openmatlab/pull/484) |
| Evidence merge tip | *(recorded by the after-epic sync PR)* | Squash merge of this acceptance PR; re-run from here or `main` |

## Verdict

**Ready for user acceptance.** #459 and #460 are closed. M2 criterion C15 is **met**. The epic issue #482 stays **open** until the user accepts it.

## Traceability — Issues → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| `["a" "b"]`, `strings`, `string(cell/num/char matrix)`, indexing/assign/grow/delete, `s{k}`, elementwise `+`/`==`, transpose/char/cellstr/isequal/for, display | #459 | [#484](https://github.com/superche/openmatlab/pull/484) | [job 114878542627](https://github.com/superche/openmatlab/actions/runs/38269076542/job/114878542627) **success** |
| `upper/lower/strip/strtrim/replace/strrep/split/join/contains/startsWith/endsWith/strcmp/strcmpi` | #460 | #484 | same |

## Functional demo (real CLI output)

```text
$ openmatlab -e 's = ["ab" "c"; "d" "ef"], z = size(s)'
s =

  2x2 string array

    "ab"    "c"
    "d"     "ef"

z =

   2   2

$ openmatlab -e 't = ["a" "b"]; t(4) = "d", t(1) = []'
t =

  1x4 string array

    "a"    "b"    <missing>    "d"

t =

  1x3 string array

    "b"    <missing>    "d"

$ openmatlab -e 'p = split("a,b,,c", ","), j = join(p, "-"), c = contains(upper(p), "B")'''
p =

  3x1 string array

    "a"
    "b"
    "c"

j =

"a-b-c"

c =

   0   1   0

$ openmatlab -e "w = strtrim('  x '), r = replace(\"aXbX\", \"X\", \"--\"), k = strcmp([\"a\" \"b\"], \"a\")"
w =

x

r =

"a--b--"

k =

   1   0

$ openmatlab -e 'x = ["a" "b"] + ["a" "b" "c"]'
error: Arrays have incompatible sizes for this operation.
```

## Measurable gate — pytest

```text
$ pytest -m "unit or bdd" --tb=no
894 passed, 2 deselected in 3.76s
$ pytest tests/conformance --tb=no
22 passed in 0.59s
$ pytest tests/unit/test_string_arrays.py tests/bdd/test_string_arrays_bdd.py "tests/conformance/test_m2_conformance.py::test_m2_criterion[C15-c15_string_arrays]"
55 passed in 0.59s
```

New cases: 50 unit (`tests/unit/test_string_arrays.py`), 4 Gherkin scenarios
(`features/string_arrays.feature`), and conformance `c15_string_arrays`.

**Existing tests changed (one):**
`tests/unit/test_int_string_classes.py::test_string_unsupported_ops_and_arrays`. It asserted that `["a" "b"]` raises "string arrays…", which was the #457 non-goal that this epic implements. That assertion now checks that `["a" "b"]` builds a 1x2 `string` and that `["a" "b"] * 2` raises the operator error. The `"a" * 2` assertion is unchanged.

**User-visible behaviour change:** `["a" "b"]` builds a string array instead of raising an error.

## Feature map (epic-related)

```text
$ openmatlab features | rg "string"
runtime.string_class             runtime    done     string scalars and string arrays
libs.string_methods              libs       done     text methods for string/char/cellstr
```

## Residuals (filed)

- [#483](https://github.com/superche/openmatlab/issues/483): `missing`/`ismissing`, `sort`/`unique` on string arrays, `split` of non-scalar arrays, `compose`/`sprintf`, regexp, `extractBetween`/`pad`…, N-D string arrays.

## Milestone progress (M2)

- Criteria met: **15 / 15** (C15 added at p2 and met by this epic)
- Conformance scripts passing: **15 / 15** (xfail pending: none)
- Remaining gaps (priority order, all p2): #451 sparse (next epic), #479 N-D cell residuals, #480 `eps(x)` relative, #483 string residuals
