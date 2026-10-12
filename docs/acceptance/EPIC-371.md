# Acceptance evidence — Epic #371 (Domain business-conformance)

**Epic:** [#371 Epic: Domain business-conformance gate (reference vectors)](https://github.com/superche/openmatlab/issues/371)  
**Scope issues:** [#373](https://github.com/superche/openmatlab/issues/373) · [#374](https://github.com/superche/openmatlab/issues/374) · [#375](https://github.com/superche/openmatlab/issues/375) · [#376](https://github.com/superche/openmatlab/issues/376)  
**Milestone:** [Domain business-conformance](https://github.com/superche/openmatlab/milestone/5) · [`docs/milestones/M-domain-conformance.md`](../milestones/M-domain-conformance.md)  
**Captured:** 2026-10-12 ~10:03 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional (D01–D04) | `91d68bac9731e7bd6ea0b306b36331cda505dc13` | Squash merge of [#383](https://github.com/superche/openmatlab/pull/383) |
| Evidence (this PR) | *(fill after merge)* | Merge of acceptance PR onto `main` |

## Verdict

**Ready for user acceptance.** Milestone exit criteria 1–4 hold on `main` (D01–D04 **met**, no open `p0` on milestone/5). Children #373–#376 closed. **Epic remains OPEN** until the user accepts.

## Traceability — Issues → PR → CI

| Criterion | Issue | PR | CI (`test`) |
|-----------|-------|----|-------------|
| D01 harness + hamming | #373 | [#383](https://github.com/superche/openmatlab/pull/383) | [run 38194219884](https://github.com/superche/openmatlab/actions/runs/38194219884) **success** |
| D02 rectwin | #374 | [#383](https://github.com/superche/openmatlab/pull/383) | same |
| D03 blackman | #375 | [#383](https://github.com/superche/openmatlab/pull/383) | same |
| D04 PluginHost which | #376 | [#383](https://github.com/superche/openmatlab/pull/383) | same |

Functional tip check-run: name=`test`, conclusion=`success`,  
https://github.com/superche/openmatlab/actions/runs/38194219884/job/114633239243

## Milestone progress (M-domain-conformance)

- Criteria met: **4 / 4** (D01–D04)
- Conformance scripts: D01–D03 pass; D04 Python gate passes
- Remaining gaps (priority order): *(none on this milestone — residuals deferred to Domain toolboxes #3 if breadth grows)*

## Feature map (epic-related)

| feature_id | status |
|------------|--------|
| `qa.domain_conformance` | partial |
| `host.extensions.community_signal` | partial |

`partial` = gate + reference vectors locked; not full signal toolbox / Domain toolboxes milestone.

## Measurable gate — pytest markers

```text
$ pytest -m "unit or bdd" --tb=no
382 passed, 2 deselected, 1 warning in 1.67s
```

Never weakened.

```text
$ pytest tests/conformance -m conformance --tb=no
18 passed in 0.43s
```

## Smoke — reference vector (`hamming(5)`)

```text
$ python - <<'PY'
... addpath community.signal/mfiles; h5 = hamming(5); ...
PY
hamming(5)= [0.08000000000000002, 0.54, 1.0, 0.5400000000000001, 0.08000000000000002]
```

## Smoke — D04 PluginHost `which`

```text
which /workspace/openmatlab/demos/plugins/community.signal/mfiles/hamming.m
```

## Residuals / non-goals

- Full Octave Forge / MATLAB Signal Toolbox parity → Domain toolboxes (milestone/3)
- Closing Epic #349 — separate user acceptance
- No residual gap Issues required for this MVP gate (criteria table complete)

## Architecture

See `docs/milestones/M-domain-conformance.md` and `docs/design/M5-domain-conformance-first.md`.
