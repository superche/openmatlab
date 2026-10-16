# Acceptance evidence: Epic #769 (G-E2 graphics object queries)

**Epic:** [#769](https://github.com/superche/openmatlab/issues/769)  
**Feature PR:** [#856](https://github.com/superche/openmatlab/pull/856) (#769)  
**Milestone:** [Graphics completion (M13)](https://github.com/superche/openmatlab/milestone/13) · [`docs/milestones/M13-graphics.md`](../milestones/M13-graphics.md)  
**Design + adversarial review:** [`docs/design/EPIC-769-object-queries.md`](../design/EPIC-769-object-queries.md)  
**Captured:** 2026-10-17 (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below come from real local commands. None are invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional tip | `b51fd792cecfedad83dd823a775a72980b394d56` | Squash merge of feature PR [#856](https://github.com/superche/openmatlab/pull/856) |
| Evidence merge tip | `1f796f12e93b4d7118c97526fdb2180e11c64172` | Squash merge of [#859](https://github.com/superche/openmatlab/pull/859); re-run from here or `main` |

## Verdict

**Ready for user acceptance.** M13 criteria G02 and G07 are **met**. Epic #769 stays **open** until the user accepts it.

`findobj` (Name/Value, `-regexp`, `-property`, `-and`/`-or`/`-xor`/`-not`, `-depth`, `'flat'`), `findall` (hidden handles), `allchild`, `ancestor` (type list, `'toplevel'`), `groot`, `gco` and `axes(fig)`. Traversal follows MATLAB Children order (newest first). This also completes G07 (text/annotation/legend, Epic #772).

## Traceability: scope → PR → CI

| Feature / case | Issue | PR | CI (`test`) |
|----------------|-------|----|-------------|
| G-E2 epic: object queries | #769 | [#856](https://github.com/superche/openmatlab/pull/856) | [job 117177502013](https://github.com/superche/openmatlab/actions/runs/38961523701/job/117177502013) **success** |

## Functional demo (real CLI output)

```text
$ openmatlab -e "f = figure('Visible','off'); hold on; l1 = plot(1:3,'Tag','a'); l2 = plot(3:-1:1,'Tag','b'); disp(numel(findobj(f,'Type','line'))); disp(isequal(findobj(f,'-regexp','Tag','^b'), l2)); disp(isequal(ancestor(l1,'figure'), f)); disp(get(groot,'Type')); close all"
2
1
1
root
```

## Measurable gate: pytest

```text
$ pytest -m "unit or bdd" --tb=no
1997 passed, 2 deselected, 9 xfailed in 80.06s (0:01:20)
$ pytest tests/unit/test_epic769_object_queries.py "tests/conformance/test_m13_conformance.py::test_m13_criterion[G02-m13_g02_findobj]" --tb=no
8 passed in 1.10s
$ pytest tests/conformance/test_m13_conformance.py --tb=no
5 passed, 6 xfailed in 1.44s
```

New cases: `tests/unit/test_epic769_object_queries.py` (7); G02 and G07 conformance flipped to met.

**Existing tests changed: none.**

## Feature map (epic-related)

```text
$ openmatlab features | rg -F libs.graphics.object_queries
libs.graphics.object_queries     libs       done     graphics object queries
```

## Residuals (filed)

| Residual | Issue |
|---|---|
| `gco` has no current-object tracking (no mouse selection in batch mode) | none (by design) |

## Milestone progress (M13)

- Criteria met: **4 / 10** (G01, G02, G04, G07)
- Conformance scripts passing: **4 / 10** (strict xfail pending: G03, G05, G06, G08, G09, G10)
- Next: G-E4 #771 (G05, G06), G-E3 #770 (G03), G-E6 #773 (G08), G-E7 #774 (G09/G10); M12 C-E5 #765.
