# Acceptance evidence: Epic #629 (JSON and delimited numeric I/O)

**Epic:** [#629](https://github.com/superche/openmatlab/issues/629)  
**Feature PR:** [#666](https://github.com/superche/openmatlab/pull/666) (#629)  
**Milestone:** [Domain toolboxes (M3)](https://github.com/superche/openmatlab/milestone/3) · [`docs/milestones/M3-domain-toolboxes.md`](../milestones/M3-domain-toolboxes.md)  
**Design + adversarial review:** [`docs/design/EPIC-629-data-io.md`](../design/EPIC-629-data-io.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `3320ba61400dd8f5b901676cdf287c960cd710b4` | Squash merge of feature PR [#666](https://github.com/superche/openmatlab/pull/666) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M3 criterion T05 is **met**. Epic #629 stays **open** until the user accepts it.

Covered:
- `jsonencode` for numerics, logicals, NaN/Inf, char/string, structs, struct arrays, cells and N-D arrays, with 'ConvertInfAndNaN' and 'PrettyPrint';
- `jsondecode` with MATLAB's consolidation rules (column vectors, matrices, N-D, null to NaN, struct arrays, cells) and makeValidName keys;
- `dlmwrite` '-append', offsets, 'newline' and precision;
- `csvread`/`dlmread` offsets (already in core since Epic #533) verified by the T05 script.

T05 is met.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| M3-E5 JSON and delimited numeric I/O (T05) | #629 | [#666](https://github.com/superche/openmatlab/pull/666) | [job 115219521884](https://github.com/superche/openmatlab/actions/runs/38374542430/job/115219521884) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "s = jsondecode('{"a":1,"b":[1,2,3],"e":null}')"
s =

  struct with fields:

    a: 1
    b: [3×1 double]
    e: []
$ openmatlab -e "jsonencode(struct('a', {1, 2}))"
ans =

[{"a":1},{"a":2}]
$ openmatlab -e "jsonencode([1 2; 3 4])"
ans =

[[1,2],[3,4]]
$ openmatlab -e "t = jsondecode('[{"x":1},{"x":2}]'); size(t)"
ans =

   2   1
$ openmatlab -e "f = [tempname '.txt']; dlmwrite(f, [1 2 3], ';'); dlmwrite(f, [4 5 6], '-append', 'delimiter', ';'); dlmread(f, ';')"
ans =

   1   2   3
   4   5   6
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1446 passed, 2 deselected, 6 xfailed in 17.99s
$ pytest tests/unit/test_json_dlm_io.py tests/bdd/test_json_dlm_io_bdd.py "tests/conformance/test_m3_conformance.py::test_m3_criterion[T05-m3_t05_data_io]" --tb=no
6 passed in 0.42s
$ pytest tests/conformance/test_m3_conformance.py --tb=no
6 passed, 2 xfailed in 0.54s
```

New cases: 3 unit tests (`tests/unit/test_json_dlm_io.py`), 2 Gherkin scenarios (`features/json_dlm_io.feature`), and conformance `m3_t05_data_io` (19 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.json_dlm_io
libs.json_dlm_io                 libs       done     jsonencode/jsondecode, dlmwrite -append/offsets/newline, csvread/dlmread offsets
```

## Residuals (filed)

- [#665](https://github.com/superche/openmatlab/issues/665) (p2): PrettyPrint layout parity, objects/Map/datetime/table in JSON, makeValidName false, dlmread range strings.

## Milestone progress (M3)

- Criteria met: **5 / 7** (T01, T02, T03, T04, T05)
- Conformance scripts passing: **5 / 7** (strict xfail pending: T06, T07)
- Next: M8 O-E5 (#622), then M3-E6 community.signal plugin (#630)
