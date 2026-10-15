# community.signal — clean-room Octave Forge–compatible windows

Contract: [`docs/design/PLUGIN-CONTRACT.md`](../../../docs/design/PLUGIN-CONTRACT.md).  
Issues: [#367](https://github.com/superche/openmatlab/issues/367) (package proof),
[#368](https://github.com/superche/openmatlab/issues/368) (desktop panel).

## What this is

A **community** domain plugin that contributes:

| Contribution | Detail |
|--------------|--------|
| `pathEntries` → `mfiles/` | `hamming`, `rectwin`, `blackman`, `hann`, `kaiser`, `butter`, `freqz`, `filtfilt` |
| Command `community.signal.demo` | Loads path + **calls** `hamming(5)` |
| Panel `community.signal.panel` | Real tk frame (title + Run button) |

**Upstream reference:** public MATLAB / [Octave Forge `signal`](https://gnu-octave.github.io/octave-signal/functions/) window API docs.  
**License of this plugin:** MIT (same as OpenMATLAB).  
**Not copied:** GPL Octave Forge sources. Clean-room from public formulas / docs.  
**Not:** MathWorks proprietary Signal Processing Toolbox.

## Try it

```bash
cd /workspace/openmatlab && . .venv/bin/activate

# Discover + activate
openmatlab plugins --path demos/plugins/community.signal --no-user-dir --no-entry-points --activate

# Call via Host API (proves real numeric output)
python - <<'PY'
from openmatlab.extensions import PluginHost
from openmatlab.libs.path import ToolboxPath
h = PluginHost(toolbox_path=ToolboxPath())
h.discover(extra=["demos/plugins/community.signal"], include_user_dir=False, include_entry_points=False)
h.load_all(); h.activate_on_startup()
print(h.execute_command("community.signal.demo"))
print("which", h.path_api.which("hamming"))
PY

# Headless panel metadata
openmatlab desktop --path demos/plugins/community.signal --list-only

# Minimal desktop (auto-close for recordings)
openmatlab desktop --path demos/plugins/community.signal --demo-ms 8000
```
