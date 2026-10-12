# M-domain-conformance — Domain business-conformance gate

GitHub milestone: https://github.com/superche/openmatlab/milestone/5

**Related:** Plugin host [`M-plugins.md`](M-plugins.md) · Domain toolboxes
(milestone/3, richer libraries after this gate) · Sample plugin
`demos/plugins/community.signal`

## Intent

Before expanding community domain toolboxes, lock a **business-conformance
gate**: public-spec **reference vectors** + pytest harness (same honesty model
as M2 — strict xfail until met). First domain: signal **window** APIs
(`hamming`, `rectwin`, `blackman`) from the clean-room community plugin.

Not MathWorks proprietary code. Clean-room / public MATLAB & Octave docs only.

## Exit criteria (measurable)

M-domain-conformance is **done** only when **all** hold on `main`:

1. **Domain conformance suite.** Every criterion in
   [`tests/conformance/domain_manifest.py`](../../tests/conformance/domain_manifest.py)
   is `met`, and `pytest tests/conformance -m conformance` reports **0 xfail**
   for domain scripts.
2. **Required feature_ids** at least `partial` with written notes (list below);
   promote to `done` only with Issue/PR criteria.
3. **No open `p0` Issue** on this milestone.
4. **Docs sync.** `PROCESS.md` / `AGENTS.md` / `ARCHITECTURE.md` point at this
   milestone.

Pending scripts run as **strict xfail** (flip to `met` in the same PR that
makes them pass).

## Criteria (priority order — epic selection)

| # | Criterion | Script | Priority | Tracking | Status |
|---|-----------|--------|----------|----------|--------|
| D01 | `hamming(n)` reference vectors (n=1,5,8) | d01_hamming | p0 | #373 | **met** |
| D02 | `rectwin(n)` reference vectors (n=1,4) | d02_rectwin | p0 | #374 | **met** |
| D03 | `blackman(n)` reference vectors (n=1,5,8) | d03_blackman | p0 | #375 | **met** |
| D04 | PluginHost path → `which hamming` gate | plugin_which (Python) | p1 | #376 | **met** |

Epic #371 takes unmet rows in this table (p0 before p1, then table order).

## Required feature_ids

`qa.domain_conformance`, `host.extensions.community_signal` (partial OK while
breadth grows).

## Non-goals

- Full Octave Forge / MATLAB Signal Toolbox parity
- Closing Domain toolboxes (milestone/3)
- Closing Epic #349 (user acceptance separate)

## Progress snapshot

**4 / 4** criteria met (D01–D04). Children #373–#376 closed via [#383](https://github.com/superche/openmatlab/pull/383).
Acceptance: [`docs/acceptance/EPIC-371.md`](../acceptance/EPIC-371.md). Epic **#371** OPEN until user accepts.
