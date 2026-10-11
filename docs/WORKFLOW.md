# Work / defect workflow (QA layer 5)

## When to open a defect

- Pytest failure that is not flake
- Architecture/review gap that blocks MVP
- Missing feature row or test case discovered in use
- User-reported incorrect behavior (once eval exists)

## Procedure

1. Copy `docs/defects/TEMPLATE.md` → `docs/defects/D####.md` (next id in `index.yaml`).
2. Add a row to `docs/defects/index.yaml`.
3. Set `type`: `bug` | `gap` | `epic` | `chore`.
4. Link `feature_ids` and optional `case_ids`.
5. Triage → `accepted` → implement → update `docs/feature_map.yaml` /
   `docs/test_catalog.yaml` → mark defect `resolved`/`closed`.

## Ownership

| Type | Default owner lens |
|------|--------------------|
| bug | package owning the failing layer (`lang`, `runtime`, …) |
| gap | architecture + feature_map update |
| epic | split into gaps/bugs before coding |
| chore | tooling/QA/docs (`openmatlab.qa`, CI) |

## CLI

```bash
openmatlab defects              # table from index.yaml
openmatlab defects --status open
```
