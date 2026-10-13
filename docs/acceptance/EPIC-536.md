# Acceptance evidence: Epic #536 (core strings)

**Epic:** [#536](https://github.com/superche/openmatlab/issues/536)  
**Feature PR:** [#590](https://github.com/superche/openmatlab/pull/590) (#555, #556)  
**Milestone:** [MATLAB core language & I/O (M7)](https://github.com/superche/openmatlab/milestone/7) · [`docs/milestones/M7-core-language-io.md`](../milestones/M7-core-language-io.md)  
**Design + adversarial review:** [`docs/design/EPIC-536-strings.md`](../design/EPIC-536-strings.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `b64f86b1a5bd3bb1e360cb443706dd3bbfd94d46` | Squash merge of feature PR [#590](https://github.com/superche/openmatlab/pull/590) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M7 criterion C07 is **met**. Epic #536 stays **open** until the user accepts it.

Covered:
- split/join/find/concat (`strsplit` with CollapseDelimiters and regex delimiters, `strjoin` with delimiter cells, overlapping `strfind` and cell input, `strcat`'s char-trim vs cell rule, `strvcat`);
- `str2num` with the `ok` flag;
- `mat2str` (precision, logical, `'class'`, char quoting, empties) and `int2str`;
- base conversions, `blanks`/`deblank`;
- `fliplr`/`flipud`/`flip` on char and cell.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| strsplit strjoin strfind strcat strvcat str2num | #555 | [#590](https://github.com/superche/openmatlab/pull/590) | [job 115148124204](https://github.com/superche/openmatlab/actions/runs/38352589873/job/115148124204) **success** |
| mat2str int2str dec2bin bin2dec hex2dec dec2hex blanks deblank | #556 | [#590](https://github.com/superche/openmatlab/pull/590) | same job |

## Functional demo (real CLI output)

```text
$ openmatlab -e "c = strsplit('a,b,,c', ',', 'CollapseDelimiters', false)"
c =

{1×4 cell}
  (1,1) = a
  (1,2) = b
  (1,3) = 
  (1,4) = c
$ openmatlab -e "s = strjoin({'x', 'y', 'z'}, '-'), f = strfind('abcabc', 'bc')"
s =

x-y-z

f =

   2   5
$ openmatlab -e "m = mat2str([1.5 NaN; -Inf 2]), k = mat2str(int8([1 2]), 'class')"
m =

[1.5 NaN;-Inf 2]

k =

int8([1 2])
$ openmatlab -e "[v, ok] = str2num('1+'); ok, w = str2num('[1 2 3]')"
ok =

0

w =

   1   2   3
$ openmatlab -e "b = dec2bin(5, 8), h = hex2dec('FF'), i = int2str([1.2 3.7])"
b =

00000101

h =

255

i =

1  4
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1276 passed, 2 deselected, 3 xfailed in 14.39s
$ pytest tests/unit/test_strfun.py tests/bdd/test_strfun_bdd.py "tests/conformance/test_m7_conformance.py::test_m7_criterion[C07-m7_c07_strings]" --tb=no
15 passed in 0.48s
$ pytest tests/conformance/test_m7_conformance.py --tb=no
8 passed, 3 xfailed in 0.53s
```

New cases: 11 unit tests (`tests/unit/test_strfun.py`), 3 Gherkin scenarios (`features/strfun.feature`), and conformance `m7_c07_strings` (35 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.strfun
libs.strfun                      libs       done     core string functions
```

## Residuals (filed)

- [#589](https://github.com/superche/openmatlab/issues/589) (p2): negative dec2bin, str2num caller workspace, string-array class rules, escape breadth.

## Milestone progress (M7)

- Criteria met: **7 / 10** (C01–C07)
- Conformance scripts passing: **7 / 10** (strict xfail pending: C08–C10)
- Next: Epic #537 (C08 graphics core)
