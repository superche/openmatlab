# community.signal — contract-aligned sample plugin

Follows [`docs/design/PLUGIN-CONTRACT.md`](../../../docs/design/PLUGIN-CONTRACT.md).

```bash
cd /workspace/openmatlab && . .venv/bin/activate
export OPENMATLAB_PLUGIN_PATH=demos/plugins/community.signal
openmatlab plugins
python -c "
from openmatlab.extensions import PluginHost
from openmatlab.libs.path import ToolboxPath
h = PluginHost(toolbox_path=ToolboxPath())
h.discover(extra=['demos/plugins/community.signal'], include_user_dir=False, include_entry_points=False)
h.load_all(); h.activate_on_startup()
print(h.execute_command('community.signal.demo'))
print(h.list_plugins())
"
```
