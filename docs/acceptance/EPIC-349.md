# Acceptance evidence — Epic #349 (Plugin host)

**Epic:** [#349 Epic: VS Code–style plugin host (community plugins)](https://github.com/superche/openmatlab/issues/349)  
**Scope issues:** [#350](https://github.com/superche/openmatlab/issues/350) · [#351](https://github.com/superche/openmatlab/issues/351) · [#352](https://github.com/superche/openmatlab/issues/352) · [#353](https://github.com/superche/openmatlab/issues/353) · [#354](https://github.com/superche/openmatlab/issues/354) · [#355](https://github.com/superche/openmatlab/issues/355) · [#356](https://github.com/superche/openmatlab/issues/356)  
**Milestone:** [Plugin host (VS Code-style)](https://github.com/superche/openmatlab/milestone/4) · [`docs/milestones/M-plugins.md`](../milestones/M-plugins.md)  
**Contract:** [`docs/design/PLUGIN-CONTRACT.md`](../design/PLUGIN-CONTRACT.md)  
**Captured:** 2026-10-11 ~23:05 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional | `55c55e82f9bbacea2a4a0bc5e411f0f7629d5acb` | Merge of [#358](https://github.com/superche/openmatlab/pull/358) |
| Evidence | *(this PR merge tip)* | Filled after acceptance PR merges |

## Verdict

**Ready for user acceptance.** M-plugins exit criteria 1–7 hold on `main` after #358. Children #350–#356 closed. Epic **remains OPEN** until the user accepts. Showcase recording: `demos/plugins/showcase_plugin_host.mp4` (same PR or follow-up if encoding lands separately).

## Traceability — Issues → PR → CI

| Criterion | Issue | PR | CI (`test`) |
|-----------|-------|----|-------------|
| P01 Contract docs | #349 / #357 | [#357](https://github.com/superche/openmatlab/pull/357) | prior green |
| P02–P08 Host | #350–#356 | [#358](https://github.com/superche/openmatlab/pull/358) | [run 38149639262](https://github.com/superche/openmatlab/actions/runs/38149639262) **success** |

Functional tip check-run: name=`test`, conclusion=`success`,  
https://github.com/superche/openmatlab/actions/runs/38149639262/job/114500213144

## Milestone progress (M-plugins)

- Criteria met: **8 / 8** (P01–P08)
- Conformance scripts: n/a (M-plugins uses unit/bdd gates, not M2 xfail scripts)
- Remaining gaps (priority order): residuals #359–#362 (all **p2**)

## Feature map (epic-related)

| feature_id | status |
|------------|--------|
| `host.extensions.manifest` | partial |
| `host.extensions.slots` | partial |
| `host.extensions.activation` | partial |
| `host.extensions.api` | partial |
| `host.extensions.discovery` | partial |
| `host.cli.plugins` | partial |
| `host.extensions.engines` | partial |

`partial` = MVP host slice + tests; not marketplace / out-of-process / rich Desktop chrome.

## Measurable gate — pytest markers

```text
$ pytest -m "unit or bdd" --tb=no
363 passed, 2 deselected, 1 warning in 1.41s
```

Never weakened.

## Smoke — CLI `plugins`

```text
$ openmatlab plugins --path demos/plugins/community.signal --no-user-dir --no-entry-points --activate
ID                           VER        STATE        ENGINES                MISMATCH
------------------------------------------------------------------------------------------
community.signal             0.1.0      active       >=0.1.0 <0.2.0         no
```

## Smoke — Host API + sample command + path entry

```text
$ python - <<'PY'
from openmatlab.extensions import PluginHost, api_version
from openmatlab.libs.path import ToolboxPath
h = PluginHost(toolbox_path=ToolboxPath())
h.discover(extra=["demos/plugins/community.signal"], include_user_dir=False, include_entry_points=False)
h.load_all(); h.activate_on_startup()
print("api_version", api_version)
print(h.execute_command("community.signal.demo"))
print("which", h.path_api.which("sigdemo"))
PY
api_version 0.1.0
[openmatlab] community.signal: demo OK (path=/workspace/openmatlab/demos/plugins/community.signal)
community.signal: demo OK (path=/workspace/openmatlab/demos/plugins/community.signal)
which /workspace/openmatlab/demos/plugins/community.signal/mfiles/sigdemo.m
```

## Architecture blurb

```text
$ openmatlab status
OpenMATLAB 0.0.2 — architecture + layered QA (off-the-shelf preferred)

Packages: host · lang · runtime · numerics · graphics · libs · extensions · qa
```

## Residual Issues

| Issue | Topic |
|-------|-------|
| [#359](https://github.com/superche/openmatlab/issues/359) | Wire `contributes.builtins` factory → FunctionResolver |
| [#360](https://github.com/superche/openmatlab/issues/360) | Activate `onPathExists` / `workspaceHasMatlabFiles` |
| [#361](https://github.com/superche/openmatlab/issues/361) | Host API `extensions.get_extension(id)` |
| [#362](https://github.com/superche/openmatlab/issues/362) | `when` clauses + richer UI panels |

## Non-goals (unchanged)

Marketplace, Option D micro-frontends, MathWorks proprietary toolbox ports.

## How to re-run

```bash
git checkout main   # or evidence tip after this PR merges
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab plugins --path demos/plugins/community.signal --no-user-dir --activate
```
