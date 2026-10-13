# Acceptance evidence: Epic #531 (functions)

**Epic:** [#531](https://github.com/superche/openmatlab/issues/531)  
**Feature PR:** [#570](https://github.com/superche/openmatlab/pull/570) (#542, #543, #544)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-531-functions.md`](../design/EPIC-531-functions.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `c962d8b3e9b6a2aab0686e0f67598c315086f7af` | Squash merge of feature PR [#570](https://github.com/superche/openmatlab/pull/570) |
| Evidence merge tip | `f8e1ce79bdcf32c2f559f91323e5ad5348d32e7b` | Squash merge of [#571](https://github.com/superche/openmatlab/pull/571); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M7 criterion C02 is **met**. Epic #531 stays **open** until the user accepts it.

These now follow MATLAB semantics:
- `varargin`/`varargout` and `nargin`/`nargout`, including the named form, plus `narginchk`/`nargoutchk`;
- the input and output count rules (`MATLAB:TooManyInputs`, `MATLAB:unassignedOutputs`; a statement call runs with nargout 0);
- `global`/`persistent`;
- `eval` (value, statement and catch-string forms), `feval`, `exist`, `str2func`/`func2str`;
- the operator functions (`plus`...`vertcat`).

The #529 script local functions shipped first, in PR #564.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| varargin/varargout, nargin/nargout (+named), narginchk/nargoutchk, I/O count rules, any value as an argument | #542 | [#570](https://github.com/superche/openmatlab/pull/570) | [job 115132515271](https://github.com/superche/openmatlab/actions/runs/38347604989/job/115132515271) **success** |
| global / persistent declarations | #543 | [#570](https://github.com/superche/openmatlab/pull/570) | same job |
| eval / feval / exist / str2func / func2str, operator functions | #544 | [#570](https://github.com/superche/openmatlab/pull/570) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "f = str2func('@(x) x.^2 + 1'); y = f(3), s = func2str(f)"
y =

10

s =

@(x)x.^2+1
$ openmatlab -e "[m, i] = feval('max', [3 9 1])"
m =

9

i =

2
$ openmatlab -e "v = eval('6 * 7'), eval('bad syntax (', 'disp(''caught'')')"
v =

42

caught
$ openmatlab -e "global G; G = 4; global G; G"
G =

4
$ openmatlab -e "a = exist('sum'), b = exist('nope_zz'), c = plus([1 2], 3)"
a =

5

b =

0

c =

   4   5
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1147 passed, 2 deselected, 8 xfailed in 14.64s
$ pytest tests/unit/test_functions_531.py tests/bdd/test_functions_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C02-m7_c02_functions]" --tb=no
26 passed in 0.52s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
3 passed, 8 xfailed in 0.43s
```

New cases: 20 unit tests (`tests/unit/test_functions_531.py`), 5 Gherkin scenarios (`features/functions.feature`), and conformance `m7_c02_functions` (32 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F lang.functions_variadic
lang.functions_variadic          lang       done     varargin/varargout, nargin/nargout, global/persistent, eval/feval, exist, str2func/func2str
```

## Residuals (filed)

- [#569](https://github.com/superche/openmatlab/issues/569) (p1): multi-collection `cellfun`/`arrayfun`, the bare `nargin` message, `evalin`/`assignin`/`inputname`, `clear` of globals.

## Milestone progress (M7)

- Criteria met: **2 / 10** (C01, C02)
- Conformance scripts passing: **2 / 10** (strict xfail pending: C03–C10)
- Next: Epic #532 (C03 command syntax)
