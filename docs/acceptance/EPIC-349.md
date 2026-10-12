# Acceptance evidence — Epic #349 (Plugin host)

**Epic:** [#349 Epic: VS Code–style plugin host (community plugins)](https://github.com/superche/openmatlab/issues/349)  
**Scope issues:** [#350](https://github.com/superche/openmatlab/issues/350) · [#351](https://github.com/superche/openmatlab/issues/351) · [#352](https://github.com/superche/openmatlab/issues/352) · [#353](https://github.com/superche/openmatlab/issues/353) · [#354](https://github.com/superche/openmatlab/issues/354) · [#355](https://github.com/superche/openmatlab/issues/355) · [#356](https://github.com/superche/openmatlab/issues/356)  
**Deepening (user rejected shallow acceptance):** [#367](https://github.com/superche/openmatlab/issues/367) · [#368](https://github.com/superche/openmatlab/issues/368)  
**Milestone:** [Plugin host (VS Code-style)](https://github.com/superche/openmatlab/milestone/4) · [`docs/milestones/M-plugins.md`](../milestones/M-plugins.md)  
**Contract:** [`docs/design/PLUGIN-CONTRACT.md`](../design/PLUGIN-CONTRACT.md)  
**Captured:** 2026-10-12 ~09:30 CST (Asia/Shanghai) on `/workspace/openmatlab`  
**Rule:** Outputs below are from real local commands; not invented.

## Dual tips

| Tip | SHA | Notes |
|-----|-----|-------|
| Functional (host P02–P08) | `55c55e82f9bbacea2a4a0bc5e411f0f7629d5acb` | Merge of [#358](https://github.com/superche/openmatlab/pull/358) |
| Evidence (prior package) | `c2066ed6831726887ca89be7c69c1af2a80cd737` | Merge of [#363](https://github.com/superche/openmatlab/pull/363) |
| Deepening (this PR) | `12f5494184d6c48420c095bd01154385abee29de` | Branch tip of [#369](https://github.com/superche/openmatlab/pull/369); fill merge SHA after land |

## Verdict

**Ready for user re-acceptance after shallow rejection.** M-plugins exit criteria 1–7 still hold. Children #350–#356 closed. **Update:** Epic #349 closed on GitHub 2026-10-12 11:13 CST (user accepted); milestone closed.

Shallow acceptance was rejected because the prior showcase only proved host plumbing (`demo OK` / `which sigdemo`). This package adds:

1. **Real community toolbox integration** (#367) — clean-room MIT subset of popular Octave Forge / MATLAB **signal window** APIs (`hamming`, `rectwin`, `blackman`) under the plugin contract; **callable** with non-trivial numeric output. Not MathWorks proprietary; no GPL Octave Forge sources copied.
2. **Minimal desktop panel** (#368 / #362-class) — host-owned tk chrome (`openmatlab desktop`) renders a real contributed panel widget (title + Run + output). Full `when`-clause evaluation stays on #362.

Showcase: `demos/plugins/showcase_plugin_host.mp4` shows **both** package load/call **and** the desktop panel.

## Traceability — Issues → PR → CI

| Criterion | Issue | PR | CI (`test`) |
|-----------|-------|----|-------------|
| P01 Contract docs | #349 / #357 | [#357](https://github.com/superche/openmatlab/pull/357) | prior green |
| P02–P08 Host | #350–#356 | [#358](https://github.com/superche/openmatlab/pull/358) | [run 38149639262](https://github.com/superche/openmatlab/actions/runs/38149639262) **success** |
| Community toolbox proof | #367 | [#369](https://github.com/superche/openmatlab/pull/369) | [run 38192243011](https://github.com/superche/openmatlab/actions/runs/38192243011) **success** |
| Minimal desktop panel | #368 | [#369](https://github.com/superche/openmatlab/pull/369) | [run 38192243011](https://github.com/superche/openmatlab/actions/runs/38192243011) **success** |

Functional tip check-run: name=`test`, conclusion=`success`,  
https://github.com/superche/openmatlab/actions/runs/38149639262/job/114500213144

## Milestone progress (M-plugins)

- Criteria met: **8 / 8** (P01–P08)
- Conformance scripts: n/a (M-plugins uses unit/bdd gates, not M2 xfail scripts)
- Remaining gaps (priority order): residuals #359–#362 (all **p2**); deepening #367/#368 addressed in this evidence package (close when user accepts)

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
| `host.cli.desktop` | partial |
| `host.extensions.community_signal` | partial |

`partial` = MVP host slice + tests; not marketplace / out-of-process / rich Desktop chrome / full `when` evaluation.

## Measurable gate — pytest markers

```text
$ pytest -m "unit or bdd" --tb=no
370 passed, 2 deselected, 1 warning in 1.54s
```

Never weakened. (Was 363; +7 for #367/#368 package/panel/BDD.)

## Smoke — CLI `plugins`

```text
$ openmatlab plugins --path demos/plugins/community.signal --no-user-dir --no-entry-points --activate
ID                           VER        STATE        ENGINES                MISMATCH
------------------------------------------------------------------------------------------
community.signal             0.1.0      active       >=0.1.0 <0.2.0         no
```

## Smoke — real community package call (`hamming`)

```text
$ python - <<'PY'
from openmatlab.extensions import PluginHost, api_version
from openmatlab.libs.path import ToolboxPath
h = PluginHost(toolbox_path=ToolboxPath())
h.discover(extra=["demos/plugins/community.signal"], include_user_dir=False, include_entry_points=False)
h.load_all(); h.activate_on_startup()
print("api_version", api_version)
print(h.execute_command("community.signal.demo"))
print("which", h.path_api.which("hamming"))
print("panels", h.window_api.list_panels())
PY
api_version 0.1.0
[openmatlab] community.signal: demo OK — hamming(5)=[0.08 0.54 1 0.54 0.08]' which=/workspace/openmatlab/demos/plugins/community.signal/mfiles/hamming.m
community.signal: demo OK — hamming(5)=[0.08 0.54 1 0.54 0.08]' which=/workspace/openmatlab/demos/plugins/community.signal/mfiles/hamming.m
which /workspace/openmatlab/demos/plugins/community.signal/mfiles/hamming.m
panels ['community.signal.panel']
```

## Smoke — desktop panel metadata

```text
$ openmatlab desktop --path demos/plugins/community.signal --list-only
community.signal.panel	Signal	Octave Forge–compatible windows (hamming / rectwin / blackman)
```

GUI: `openmatlab desktop --path demos/plugins/community.signal --demo-ms 8000`  
(Recording helper: `demos/plugins/record_showcase.sh`)

## Architecture blurb

```text
$ openmatlab status
OpenMATLAB 0.0.2 — architecture + layered QA (off-the-shelf preferred)

Packages: host · lang · runtime · numerics · graphics · libs · extensions · qa
```

## Residual Issues

| Issue | Topic |
|-------|-------|
| [#359](https://github.com/superche/openmatlab/issues/359) | Wire `contributes.builtins` factory → FunctionResolver — **done** (this residual PR) |
| [#360](https://github.com/superche/openmatlab/issues/360) | Activate `onPathExists` / `workspaceHasMatlabFiles` — **done** |
| [#361](https://github.com/superche/openmatlab/issues/361) | Host API `extensions.get_extension(id)` — **done** |
| [#362](https://github.com/superche/openmatlab/issues/362) | `when` subset + richer UI panels — **done** (`when` documented+evaluated; panel chrome via #368) |
| [#367](https://github.com/superche/openmatlab/issues/367) | Real community toolbox proof *(this package)* |
| [#368](https://github.com/superche/openmatlab/issues/368) | Minimal desktop panel *(this package)* |

## Non-goals (unchanged)

Marketplace, Option D micro-frontends, MathWorks proprietary toolbox ports.

## How to re-run

```bash
git checkout main   # or deepening tip after this PR merges
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -m "unit or bdd" --tb=no
openmatlab plugins --path demos/plugins/community.signal --no-user-dir --activate
openmatlab desktop --path demos/plugins/community.signal --list-only
# optional GUI / recording:
# openmatlab desktop --path demos/plugins/community.signal --demo-ms 8000
# DISPLAY=:2 ./demos/plugins/record_showcase.sh
```
