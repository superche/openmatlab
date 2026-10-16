# Acceptance evidence: Epic #694 (T-E4 readtable/writetable/readcell/writecell)

**Epic:** [#694](https://github.com/superche/openmatlab/issues/694)  
**Feature PR:** [#722](https://github.com/superche/openmatlab/pull/722) (#694, #721)  
**Milestone:** [Tables and data types (M10)](https://github.com/superche/openmatlab/milestone/10) · [`docs/milestones/M10-tables.md`](../milestones/M10-tables.md)  
**Design + adversarial review:** [`docs/design/EPIC-694-readtable.md`](../design/EPIC-694-readtable.md)  
**Captured:** 2026-10-16 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `d1df559eaa02739cf4d11e9a395af080e940a2ce` | Squash merge of feature PR [#722](https://github.com/superche/openmatlab/pull/722) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M10 criterion T08 is **met**. Epic #694 stays **open** until the user accepts it.

T08 is met by this epic (delimited text only; spreadsheets are a milestone non-goal). The readtable part of #577 is absorbed; #577 itself stays on the Core backlog untouched.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| T08 readtable/writetable/readcell/writecell | #694 | [#722](https://github.com/superche/openmatlab/pull/722) | [job 116804573110](https://github.com/superche/openmatlab/actions/runs/38848594603/job/116804573110) **success** |
| residual | #721 | [#722](https://github.com/superche/openmatlab/pull/722) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "f = [tempname '.csv']; writetable(table([1;NaN], {'x, y';'z'}, 'VariableNames', {'a','b'}), f); disp(fileread(f)); R = readtable(f)"
a,b
1,"x, y"
,z

R =

  2×2 table

     a        b
     _        _

      1    {'x, y'}
    NaN    {'z'}
$ openmatlab -e "f = [tempname '.csv']; writecell({1,'a';2,'b'}, f); C = readcell(f); class(C{2,1})"
ans =

double
$ openmatlab -e "readtable('no_such_file.csv')"
error: Unable to find or open 'no_such_file.csv'. Check the path and filename or file permissions.
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1607 passed, 2 deselected, 11 xfailed in 17.78s
$ pytest tests/unit/test_table_io.py tests/bdd/test_table_io_bdd.py "tests/conformance/test_m10_conformance.py::test_m10_criterion[T08-m10_t08_readtable_writetable]" --tb=no
19 passed in 0.41s
$ pytest tests/conformance/test_m10_conformance.py --tb=no
5 passed, 6 xfailed in 0.37s
```

New cases: `tests/unit/test_table_io.py` (15), `tests/bdd/test_table_io_bdd.py` (3), M10 T08 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.table_io
libs.table_io                    libs       done     readtable/writetable/readcell/writecell for delimited text
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| import options, VariableDescriptions for modified headers, VariableNamingRule, encodings, more date formats, QuoteStrings/append | [#721](https://github.com/superche/openmatlab/issues/721) |

## Milestone progress (M10)

- Criteria met: **4 / 10** (T01, T02, T04, T08)
- Conformance scripts passing: **4 / 10** (strict xfail pending: T03, T05, T06, T07, T09, T10)
- Next: D-E4 #701 (Workbench debug UI), then T-E3 #693 / T-E5 #695.
