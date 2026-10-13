# Acceptance evidence: Epic #535 (core arrays and sets)

**Epic:** [#535](https://github.com/superche/openmatlab/issues/535)  
**Feature PR:** [#586](https://github.com/superche/openmatlab/pull/586) (#553, #554)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-535-arrays-sets.md`](../design/EPIC-535-arrays-sets.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `6d3120dc918a3da1ead3e145ed082e437edff142` | Squash merge of feature PR [#586](https://github.com/superche/openmatlab/pull/586) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M7 criterion C06 is **met**. Epic #535 stays **open** until the user accepts it.

Covered:
- array builders (`repmat`, `logspace`, `meshgrid`/`ndgrid`, `cell2mat`/`num2cell`/`iscellstr`, `rot90`, `tril`/`triu`, `diag`, `blkdiag`, `sub2ind`/`ind2sub`, `isequaln`);
- one set engine over numeric/char/cellstr with `'stable'`/`'rows'`/`'last'` and 1-based index outputs;
- `sortrows` with column specs, descending and NaN rules;
- `[~, i] = f(...)` output placeholders.

One existing test changed with explicit user approval (`unique` 'stable').

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| repmat kron horzcat vertcat logspace meshgrid ndgrid cell2mat num2cell iscellstr | #553 | [#586](https://github.com/superche/openmatlab/pull/586) | [job 115145844277](https://github.com/superche/openmatlab/actions/runs/38351868428/job/115145844277) **success** |
| union intersect setdiff setxor ismember sortrows; unique/isequal on cellstr | #554 | [#586](https://github.com/superche/openmatlab/pull/586) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "[c, ia, ib] = intersect([5 1 3], [3 5 7])"
c =

   3   5

ia =

   3
   1

ib =

   1
   2
$ openmatlab -e "u = unique({'z', 'y', 'z'}), s = unique([3 1 2 3], 'stable')"
u =

{1×2 cell}
  (1,1) = y
  (1,2) = z

s =

   3   1   2
$ openmatlab -e "[tf, loc] = ismember({'a', 'q'}, {'q', 'a', 'a'})"
tf =

   1   1

loc =

   2   1
$ openmatlab -e "B = sortrows([1 2; 1 1; 0 5], -2)"
B =

   0   5
   1   2
   1   1
$ openmatlab -e "[~, i] = max([1 3]), R = repmat([1 2], 2, 2)"
i =

2

R =

   1   2   1   2
   1   2   1   2
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1260 passed, 2 deselected, 4 xfailed in 13.90s
$ pytest tests/unit/test_arrays_sets.py tests/bdd/test_arrays_sets_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C06-m7_c06_arrays_sets]" --tb=no
18 passed in 0.44s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
7 passed, 4 xfailed in 0.49s
```

New cases: 13 unit tests (`tests/unit/test_arrays_sets.py`), 1 added positive test in `tests/unit/test_unique_rows.py`, 4 Gherkin scenarios (`features/arrays_sets.feature`), and conformance `m7_c06_arrays_sets` (26 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.arrays_sets
libs.arrays_sets                 libs       done     array builders, sets and sorting
```

## Residuals (filed)

- [#585](https://github.com/superche/openmatlab/issues/585) (p2): N-D repmat/num2cell on cells, union([],[]) empty shape, set ops on struct/table/string, 'legacy', `~` in function input lists.

## Milestone progress (M7)

- Criteria met: **6 / 10** (C01–C06)
- Conformance scripts passing: **6 / 10** (strict xfail pending: C07–C10)
- Next: Epic #536 (C07 strings)
