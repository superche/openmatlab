# Test catalog (human index)

**Source of truth:** [`test_catalog.yaml`](test_catalog.yaml)

Dump: `openmatlab cases`  
Design: [`QA.md`](QA.md) layer 2  
Narratives (optional): [`use_cases/`](use_cases/)

## Kinds

| Kind | Meaning |
|------|---------|
| `use_case` | User journey / goal (may span many features) |
| `test_case` | Concrete verification (`unit` / `conformance` / `interactive`) |

## Update rule

When adding a pytest that guards a capability: add/activate a `test_case` row
with `impl: path::node` and link `features: […]`. Prefer linking to layer-1
ids rather than restating status there.
