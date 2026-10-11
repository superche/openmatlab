# Option B — Manifest YAML + load path (ToolboxPath-like)

Each toolbox folder has `plugin.yaml`. Host walks an ordered load path
(like `addpath` / `ToolboxPath`), reads manifests, imports advertised
modules, and merges domain + UI contributions.

Fits MATLAB users who already think in path + toolbox folders.
