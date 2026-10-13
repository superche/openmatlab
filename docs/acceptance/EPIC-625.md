# Acceptance evidence: Epic #625 (FFT family)

**Epic:** [#625](https://github.com/superche/openmatlab/issues/625)  
**Feature PR:** [#642](https://github.com/superche/openmatlab/pull/642) (#625)  
**Milestone:** [Domain toolboxes (M3)](https://github.com/superche/openmatlab/milestone/3) · [`docs/milestones/M3-domain-toolboxes.md`](../milestones/M3-domain-toolboxes.md)  
**Design + adversarial review:** [`docs/design/EPIC-625-fft.md`](../design/EPIC-625-fft.md)  
**Captured:** 2026-10-13 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `897caeb7bd710cd7a08d7091677890a3a987cdb0` | Squash merge of feature PR [#642](https://github.com/superche/openmatlab/pull/642) |
| Evidence merge tip | _recorded by follow-up sync PR_ | Squash merge of this acceptance PR |

## Verdict

**Ready for user acceptance.** M3 criterion T01 is **met**. Epic #625 stays **open** until the user accepts it.

Covered:
- `fft`/`ifft` with `n` (pad/truncate, `[]`) and `dim`, defaulting to the first non-singleton dimension;
- `ifft` 'symmetric';
- `fft2`/`ifft2` with sizes, `fftn`/`ifftn`;
- `fftshift`/`ifftshift` with an optional dim;
- `nextpow2`, elementwise.

T01 is met.

No existing test changed.

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| M3-E1 FFT family (T01) | #625 | [#642](https://github.com/superche/openmatlab/pull/642) | [job 115193836353](https://github.com/superche/openmatlab/actions/runs/38366826399/job/115193836353) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "X = fft([1 2 3 4])"
X =

   10 + 0i   -2 + 2i   -2 + 0i   -2 - 2i
$ openmatlab -e "real(ifft(fft([4 1 2 3])))"
ans =

   4   1   2   3
$ openmatlab -e "fftshift(1:5)"
ans =

   4   5   1   2   3
$ openmatlab -e "nextpow2([100 1024])"
ans =

    7   10
$ openmatlab -e "addpath('demos/fft'); fft_demo"
peaks =

    5   12

n =

7
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1390 passed, 2 deselected, 12 xfailed in 19.41s
$ pytest tests/unit/test_fft.py tests/bdd/test_fft_bdd.py "tests/conformance/test_m3_conformance.py::test_m3_criterion[T01-m3_t01_fft]" --tb=no
9 passed in 0.45s
$ pytest tests/conformance/test_m3_conformance.py --tb=no
2 passed, 6 xfailed in 0.45s
```

New cases: 6 unit tests (`tests/unit/test_fft.py`), 2 Gherkin scenarios (`features/fft.feature`), and conformance `m3_t01_fft` (16 checks) flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F numerics.fft
numerics.fft                     numerics   done     FFT family (fft/ifft/fft2/ifft2/fftn/ifftn/fftshift/ifftshift/nextpow2)
```

## Residuals (filed)

- [#630](https://github.com/superche/openmatlab/issues/630) (M3-E6): `filtfilt` and the rest of signal breadth in the community.signal plugin.

## Milestone progress (M3)

- Criteria met: **1 / 7** (T01)
- Conformance scripts passing: **1 / 7** (strict xfail pending: T02, T03, T04, T05, T06, T07)
- Next: O-E3 property validation (#620), then M3-E2 polynomials/interpolation (#626)
