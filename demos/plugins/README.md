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

## Control examples in this directory

`tf` and `step` in [`option-b/toolboxes/control_tb/commands.py`](option-b/toolboxes/control_tb/commands.py) return the strings `tf(...)` and `step(...)`. [`option-d/bundles/control_mfe/__init__.py`](option-d/bundles/control_mfe/__init__.py) registers `step` the same way and returns a panel-label string. These are architectural stubs from the plugin-shape samples. They do not build a transfer-function value, and they do not compute a step response. This is not a computational control toolbox.

[中文](#本目录里的控制示例).

## 本目录里的控制示例

[`option-b/toolboxes/control_tb/commands.py`](option-b/toolboxes/control_tb/commands.py) 里的 `tf` 与 `step` 返回字符串 `tf(...)` 和 `step(...)`。[`option-d/bundles/control_mfe/__init__.py`](option-d/bundles/control_mfe/__init__.py) 以同样方式注册 `step`，并返回一段面板标签字符串。它们是插件形态示例里的架构桩。它们不构造传递函数的值，也不计算阶跃响应。这不是可计算的控制工具箱。

[English](#control-examples-in-this-directory).

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


## Domain conformance showcase (Epic #371)

Clear large-font terminal recording for the Domain business-conformance gate:

1. Reference-vector pytest suite (`tests/conformance`)
2. `hamming(8)` vs golden (D01)
3. PluginHost `which('hamming')` gate (D04)

- [`showcase_domain_conformance.mp4`](showcase_domain_conformance.mp4)
- Re-record: `bash demos/plugins/record_domain_conformance_showcase.sh`

Epic #371 stays OPEN until user accepts. Milestone: [`M-domain-conformance.md`](../../docs/milestones/M-domain-conformance.md).
