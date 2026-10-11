# Design: thicken M2 conformance (Issue #297)

**Epic:** #296 · Honesty follow-up to adversarial M2 review

## Decision
1. Extend `test_m2_conformance.py` expected JSON: scalar/array string tokens `"Inf"`, `"-Inf"`, `"NaN"` → float specials; NaN compares via `isnan`.
2. C04: add `p=pi`, `y=Inf`, `z=-Inf` (keep existing builtins checks).
3. C06: after vector delete, `c={1,2,3}; c(2)=[]; yc=c{1}+c{2}` → 4.
4. C08: after vector grow, `c={1}; c{3}=9; yg=c{1}+c{3}` → 10.
5. C10: add `cellfun(@sum,c)` and `cellfun(@max,c)`.

## Non-goals
New product features; weakening any assertion; closing M2.
