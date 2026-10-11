# Contributing to OpenMATLAB

Clean-room / public specs only — **no** reverse engineering of MATLAB binaries.

## Quick path

1. Open or claim a **GitHub Issue** (`gap` / `bug` / `epic` + `layer:*`).
2. Add/adjust a **Gherkin** scenario under `features/` when behaviour changes.
3. Implement against package seams (`host` / `lang` / `runtime` / …).
4. Run `pytest -m "unit or bdd"` (CI will re-run on your PR).
5. Sync `docs/feature_map.yaml` / `docs/test_catalog.yaml` if needed.
6. Fill the **PR QA checklist**.

Readiness: [`docs/READY.md`](docs/READY.md).  
Full loop and Definition of Done: **[`docs/PROCESS.md`](docs/PROCESS.md)**.  
QA layers: [`docs/QA.md`](docs/QA.md). Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
