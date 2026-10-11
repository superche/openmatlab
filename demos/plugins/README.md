# Plugin architecture demos

Four minimal, **stdlib-first** stubs exploring how OpenMATLAB could treat
**domains** and **Desktop/UI** as plugins (domains may customize UX).

| Dir | Option | One-liner |
|-----|--------|-----------|
| `option-a/` | Entry points (`importlib.metadata`) | Pip-installable plugins via package metadata |
| `option-b/` | Manifest YAML + load path | ToolboxPath-like folders with `plugin.yaml` |
| `option-c/` | Host slots + thin adapters | Host owns named extension points; plugins adapt |
| `option-d/` | Micro-frontend-ish UI | Isolated UI bundles + host shell composition |

Comparison + recommendation: [`docs/design/PLUGIN-OPTIONS.md`](../../docs/design/PLUGIN-OPTIONS.md).

```bash
cd /workspace/openmatlab
. .venv/bin/activate   # optional; demos need only stdlib (+ PyYAML for B)
python demos/plugins/option-a/run_demo.py
python demos/plugins/option-b/run_demo.py
python demos/plugins/option-c/run_demo.py
python demos/plugins/option-d/run_demo.py
```

**Not** the final plugin contract — pick an option first, then lock contract + milestone.
