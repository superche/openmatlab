# Acceptance evidence: Epic #530 (errors and exceptions)

**Epic:** [#530 Epic: errors & exceptions (C01)](https://github.com/superche/openmatlab/issues/530)  
**Feature PR:** [#566](https://github.com/superche/openmatlab/pull/566) (#540, #541)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-530-errors.md`](../design/EPIC-530-errors.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `2bf6933a378e91468f27732d8b32bed8235ef8cd` | Squash merge of feature PR [#566](https://github.com/superche/openmatlab/pull/566) |
| Evidence merge tip | `1f7d5b547c6ada6238d19f29c494cec4a5fbff0f` | Squash merge of [#567](https://github.com/superche/openmatlab/pull/567); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M7 criterion C01 is **met**. Epic #530 stays **open** until the user accepts it.

The following now work:
- `try`/`catch [e]`;
- `error` in all its forms: literal, `id`+`fmt`, struct, and empty as a no-op;
- `MException`, `throw`, `rethrow` and `getReport`;
- `assert` and `lasterr`.

Builtin errors carry MATLAB identifiers, and `break`/`continue`/`return` are never caught.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| `try/catch [ident]` grammar and evaluation; `error` forms; `MException`/`throw`/`rethrow`/`getReport`; MException class, display and `isstruct` | #540 | [#566](https://github.com/superche/openmatlab/pull/566) | [job 115122524437](https://github.com/superche/openmatlab/actions/runs/38344465635/job/115122524437) **success** |
| `assert`, `lasterr` (1 and 2 outputs), MATLAB identifiers on builtin errors (`badsubscript`, `UndefinedFunction`, `sizeDimensionsMustMatch`, ...) | #541 | [#566](https://github.com/superche/openmatlab/pull/566) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "try, error('my:id','value %d too big',7), catch e, e, end"
e =

  MException with properties:

    identifier: 'my:id'
       message: 'value 7 too big'
         stack: [0×1 struct]

$ openmatlab -e "x=[1 2 3]; try, x(5), catch e, disp(e.identifier), disp(e.message), end"
MATLAB:badsubscript
Index exceeds the number of array elements. Index must not exceed 3.
$ openmatlab -e "try, try, throw(MException('pkg:fn','bad %s','input')), catch e, rethrow(e), end, catch o, disp(o.identifier), end"
pkg:fn
$ openmatlab -e "n=0; for i=1:5, try, n=n+1; if i==2, break; end; catch, n=100; end; end, n"
n =

2

$ openmatlab -e "try, assert(1==2,'check failed %d',3), catch e, end, [m,id]=lasterr"
m =

check failed 3

id =



$ openmatlab -e "error('top:id','boom')"
error: boom
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1120 passed, 2 deselected, 9 xfailed in 14.30s
$ pytest tests/unit/test_errors.py tests/bdd/test_errors_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C01-m7_c01_errors]"
23 passed in 1.01s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
2 passed, 9 xfailed in 0.43s
```

New cases:
- 18 unit tests (`tests/unit/test_errors.py`);
- 5 Gherkin scenarios (`features/errors.feature`);
- conformance `m7_c01_errors`, flipped from strict-xfail to met. It has 16 checks.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg try_catch
lang.try_catch                   lang       done     try/catch, error, MException, assert, lasterr
```

## Residuals (filed)

- [#565](https://github.com/superche/openmatlab/issues/565) (p2) covers:
  - the size-mismatch message is NumPy-worded;
  - `MException.stack` is empty;
  - the `getReport` trace;
  - `addCause`, `throwAsCaller` and the `lasterror` struct.

## Milestone progress (M7)

- Criteria met: **1 / 10** (C01)
- Conformance scripts passing: **1 / 10** (strict xfail pending: C02–C10)
- Next: Epic #531 (C02 functions)
