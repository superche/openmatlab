# Plugin architecture demos

Four minimal, **stdlib-first** stubs that informed the locked
**VS Code–style** plugin contract.

**Normative contract:** [`docs/design/PLUGIN-CONTRACT.md`](../../docs/design/PLUGIN-CONTRACT.md)  
**Milestone:** [`docs/milestones/M-plugins.md`](../../docs/milestones/M-plugins.md)  
**Historical comparison:** [`docs/design/PLUGIN-OPTIONS.md`](../../docs/design/PLUGIN-OPTIONS.md)

| Dir | Option | Role under contract |
|-----|--------|---------------------|
| `option-a/` | Entry points (`importlib.metadata`) | Optional packaging/distribution |
| `option-b/` | Manifest YAML + load path | Default discovery/authoring shape |
| `option-c/` | Host slots + thin adapters | Normative extension surface |
| `option-d/` | Micro-frontend-ish UI | Deferred (web workbench) |

Contract-aligned sample: **`community.signal/`** (criterion P07).
Historical option stubs remain under `option-{a,b,c,d}/`.

```bash
cd /workspace/openmatlab
. .venv/bin/activate   # optional; demos need only stdlib (+ PyYAML for B)
python demos/plugins/option-a/run_demo.py
python demos/plugins/option-b/run_demo.py
python demos/plugins/option-c/run_demo.py
python demos/plugins/option-d/run_demo.py
```


## Showcase recording

Screen recording proving **both**:

1. Community package **load + call** (`hamming` via path / `community.signal.demo`)
2. Minimal **desktop panel** contribution (`openmatlab desktop`)

- [`showcase_plugin_host.mp4`](showcase_plugin_host.mp4)

Issues: #367 (toolbox proof), #368 (panel). Epic #349 stays OPEN until user accepts.
