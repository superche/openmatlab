# Acceptance evidence — Epic #1

**Epic:** [#1 MVP: Array-first fill order (matrix workbench)](https://github.com/superche/openmatlab/issues/1)  
**Scope issues:** [#2](https://github.com/superche/openmatlab/issues/2) · [#3](https://github.com/superche/openmatlab/issues/3) · [#4](https://github.com/superche/openmatlab/issues/4) · [#5](https://github.com/superche/openmatlab/issues/5) · [#6](https://github.com/superche/openmatlab/issues/6)  
**Evidence tip (epic close):** `04edfe6d1d1ecb965ec7ea0812bbec5acb737514`  
**Captured:** 2026-10-11 15:43 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Verdict

**Accepted** for the epic’s MVP fill order: Array + NumPy backend, matrix lexer/parser, evaluator/display/`-e`/REPL, plot MVP, and path `.m` function load/eval are demonstrable and gated by CI check **`test`**.

Residual (explicitly out of epic DoD): nested functions, `nargin`/`nargout`, multi-assign `[a,b]=f()`, broader control-flow, rich toolboxes, interactive (non-Agg) plot show.

## Traceability — Issues → PRs → merge SHAs → CI

| Issue | Closing PR | Merge commit | CI (`test`) |
|-------|------------|--------------|-------------|
| #2 Array + NumPy | [#10](https://github.com/superche/openmatlab/pull/10) | `2bc596b9a9deffa6f603e9fc01676f8c12ee6ce2` | required check green on merge |
| #3 Matrix lexer/parser | [#11](https://github.com/superche/openmatlab/pull/11) | `ec17c6a0bb23aa2bc39f4cdcbfa16be0e42547ea` | required check green on merge |
| #4 Evaluator + Display | [#13](https://github.com/superche/openmatlab/pull/13) (design [#12](https://github.com/superche/openmatlab/pull/12)) | `4b9d34d4af8f2669e3d62a6733001fad7987c078` | required check green on merge |
| #5 Plot MVP | [#14](https://github.com/superche/openmatlab/pull/14) | `61c301526c7ebebf842f22996c7e9023f8b2e810` | [run](https://github.com/superche/openmatlab/actions/runs/38121861356) success |
| #6 Path + `.m` eval | [#15](https://github.com/superche/openmatlab/pull/15) slice1 · [#16](https://github.com/superche/openmatlab/pull/16) complete | tip `04edfe6d1d1ecb965ec7ea0812bbec5acb737514` | [run on tip](https://github.com/superche/openmatlab/actions/runs/38122080461) **success** (`test`) |

Tip check-run (API): name=`test`, conclusion=`success`, job URL  
https://github.com/superche/openmatlab/actions/runs/38122080461/job/114418714004

## Feature map statuses (epic-related)

Source: `openmatlab features` at tip `04edfe6…` (counts overall: done=6, partial=28, stub=2).

| feature_id | status | maps to |
|------------|--------|---------|
| `runtime.value_array_protocol` | done | #2 |
| `numerics.array_backend` | done | #2 |
| `numerics.numpy_backend` | partial | #2 |
| `numerics.array_value` | partial | #2 |
| `lang.lexer` / `lang.parser` | partial | #3 |
| `lang.matrix_literal` / `lang.indexing_colon` / `lang.elementwise_ops` | partial | #3 |
| `runtime.evaluator` | partial | #4 |
| `host.display_policy` / `host.repl` | partial | #4 |
| `host.plot_surface` / `graphics.matplotlib` / `graphics.plot_mvp` | partial | #5 |
| `libs.toolbox_path` / `libs.mfile_loading` | partial | #6 |
| `runtime.function_resolver` / `lang.function_def` | partial | #6 |

`partial` here means MVP slice landed; not full MATLAB parity.

## Measurable gate — pytest markers

```text
$ pytest -m "unit or bdd" --tb=no
.....................................................................    [100%]
69 passed, 2 deselected in 0.60s
```

## Smoke — CLI demos (#2 / #3 / #4 / #5)

```text
$ openmatlab -e "A = [1 2; 3 4]"
A =

[[1. 2.]
 [3. 4.]]

$ openmatlab -e "B = [1 2; 3 4] * [1; 0]"
B =

[[1.]
 [3.]]

$ openmatlab -e "x = 1:3"
x =

[[1. 2. 3.]]

$ openmatlab -e "y = (1:3) .* 2"
y =

[[2. 4. 6.]]

$ openmatlab -e "plot(1:5, [1 4 9 16 25])"
ans =

1
```

Notes: `*` is matmul; `.*` is elementwise; plot MVP returns scalar `1` (Agg backend; no interactive window required for CI).

## Smoke — `.m` path function (#6)

`openmatlab -e` does not yet expose `addpath` as language builtin; acceptance uses the same Session/REPL path wiring production uses:

```text
$ python - <<'PY'
from pathlib import Path
import tempfile
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

tmp = Path(tempfile.mkdtemp())
(tmp / "add2.m").write_text("function y = add2(a, b)\ny = a + b;\nend\n")
s = Session.create_default()
s.path.addpath(tmp)
print("which:", s.functions.which("add2"))
ReplSession(s).run_line("r = add2(10, 5)")
print("workspace r:", float(s.workspace.get("r").backend_buffer().reshape(-1)[0]))
PY
which: /tmp/tmpgn16xbtf/add2.m
r =

15

workspace r: 15.0
```

## Architecture status blurb (host)

```text
$ openmatlab status
OpenMATLAB 0.0.2 — architecture + layered QA (off-the-shelf preferred)

Packages: host · lang · runtime · numerics · graphics · libs · qa

QA layers (docs/QA.md):
  1. Features     docs/feature_map.yaml      → openmatlab features
  2. Cases        Gherkin+pytest-bdd + catalog → openmatlab cases
  3. Environments tests/{unit,conformance,interactive}
  4. Tooling      pytest-bdd · coverage · Actions · gh
  5. Defects      GitHub Issues (canonical)  → openmatlab defects / gh issue

Interactive UI later: Playwright/Selenium only when a web workbench exists.
Eval: openmatlab -e "..." · REPL when no args. docs/ARCHITECTURE.md
```

## How to re-run

```bash
git checkout 04edfe6d1d1ecb965ec7ea0812bbec5acb737514
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab -e "A = [1 2; 3 4]"
```
