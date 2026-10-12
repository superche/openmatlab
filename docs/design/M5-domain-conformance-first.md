# Design: Domain business-conformance first slice (Epic #371)

## Approach

Reuse the M2 honesty model: `domain_manifest.py` + `.m` scripts +
`.expected.json` + strict xfail for pending rows. Harness `addpath`s
`demos/plugins/community.signal/mfiles` for D01–D03. D04 uses PluginHost
discover → activate → `which("hamming")` (no Session `addpath` in the test).

## Reference formula sources

Public MATLAB / Octave documentation semantics (clean-room). Not GPL Octave
Forge sources; not MathWorks proprietary.
