# Work / defect workflow (QA layer 5) — GitHub Issues

**Canonical tracker:** GitHub Issues on the repo (`gh` CLI / web UI).  
**Not canonical:** in-repo markdown/YAML defect ledgers (removed as source of truth).

## Prefer off-the-shelf

| Need | Tool |
|------|------|
| File / triage / close work | **GitHub Issues** + labels |
| Automate from terminal | **`gh issue`** |
| Link to capabilities | Issue body fields `feature_ids` / `case_ids` + labels `feature:<id>`, `layer:<pkg>` |
| Optional board later | GitHub Projects (not required now) |

## When to open an issue

- Pytest failure that is not flake
- Architecture/review gap that blocks MVP
- Missing feature row or test case discovered in use
- User-reported incorrect behavior (once eval exists)

## Procedure

1. Prefer template: **Bug** or **Gap** under `.github/ISSUE_TEMPLATE/`.
2. Fill **feature_ids** (from `docs/feature_map.yaml`) and optional **case_ids**
   (from `docs/test_catalog.yaml`).
3. Add labels: `bug`|`gap`|`epic`|`chore`, and `layer:runtime` (etc.).
4. Implement → update `feature_map.yaml` / `test_catalog.yaml` in the same PR.
5. Close the issue with a short resolution note / PR link.

```bash
gh issue list
gh issue list --label gap
gh issue create   # or use web / templates
openmatlab defects   # prints gh commands + runs `gh issue list` if available
```

## Ownership (by label)

| Type | Default lens |
|------|----------------|
| bug | package owning the failing layer |
| gap | architecture + feature_map update |
| epic | split into gaps/bugs before coding |
| chore | tooling/QA/docs / CI |

## What we do *not* maintain

- `docs/defects/D####.md` as a second ticket database
- `openmatlab.qa.defects` YAML index as source of truth
