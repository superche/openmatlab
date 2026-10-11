# Defects — GitHub Issues (canonical)

**OpenMATLAB does not use an in-repo defect database.**

| Concern | Off-the-shelf |
|---------|----------------|
| Bugs / gaps / epics | **GitHub Issues** on `superche/openmatlab` |
| CLI | `gh issue list` · `gh issue create` · `openmatlab defects` (thin wrapper) |
| Templates | `.github/ISSUE_TEMPLATE/` |
| Labels | `bug`, `gap`, `epic`, `chore`, `layer:*`, optional `feature:<id>` |

Workflow: [`../WORKFLOW.md`](../WORKFLOW.md) · QA layers: [`../QA.md`](../QA.md)

### File an issue (example epic)

```bash
gh issue create --title "Epic: concrete Array + evaluator" \
  --label "epic,layer:runtime" \
  --body "$(cat <<'MD'
## Summary
Leave architecture stage: Array + lexer/parser + evaluator.

## feature_ids
- runtime.evaluator
- numerics.array_value
- lang.lexer
- lang.parser

## case_ids
- uc.matrix_first_repl

## Acceptance
See docs/QA.md MVP fill order / docs/ARCHITECTURE.md
MD
)"
```
