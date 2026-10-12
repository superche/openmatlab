"""P04/P05/P08: activation, Host API, fault isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.extensions.host import PluginHost
from openmatlab.extensions.manifest import load_manifest
from openmatlab.libs.path import ToolboxPath
from openmatlab.runtime.session import Session

pytestmark = pytest.mark.unit

SAMPLE = Path("demos/plugins/community.signal")


def _host_with_sample(tmp_path: Path | None = None) -> PluginHost:
    path = ToolboxPath()
    host = PluginHost(toolbox_path=path)
    manif = load_manifest(SAMPLE)
    host.register_manifest(manif)
    return host


def test_activation_on_startup_and_command():
    host = _host_with_sample()
    host.bind_apis()
    host.load_all()
    assert host.plugins["community.signal"].state.value == "loaded"
    host.activate_on_startup()
    rec = host.plugins["community.signal"]
    assert rec.state.value == "active"
    result = host.execute_command("community.signal.demo")
    assert "demo OK" in result
    assert host.window_api.messages
    assert "community.signal.panel" in host.window_api.panels


def test_deferred_on_command_only(tmp_path: Path):
    root = tmp_path / "lazy"
    root.mkdir()
    (root / "plugin.yaml").write_text(
        """
id: community.lazy
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - onCommand:community.lazy.go
contributes:
  commands:
    - command: community.lazy.go
      title: Go
""",
        encoding="utf-8",
    )
    (root / "extension.py").write_text(
        """
def activate(context):
    context.host.commands.register_command(
        "community.lazy.go", lambda: "lazy-ok"
    )
""",
        encoding="utf-8",
    )
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    host.register_manifest(load_manifest(root))
    host.load_all()
    assert host.plugins["community.lazy"].state.value == "loaded"
    # startup should NOT activate
    host.activate_on_startup()
    assert host.plugins["community.lazy"].state.value == "loaded"
    out = host.execute_command("community.lazy.go")
    assert out == "lazy-ok"
    assert host.plugins["community.lazy"].state.value == "active"


def test_faulted_plugin_does_not_kill_session():
    root = Path("demos/plugins/community.signal").resolve()
    # Use a temp copy that raises
    import tempfile, shutil, textwrap

    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.plug"
        shutil.copytree(root, bad)
        (bad / "extension.py").write_text(
            "def activate(context):\n    raise RuntimeError('boom')\n",
            encoding="utf-8",
        )
        # rewrite id
        yaml = (bad / "plugin.yaml").read_text(encoding="utf-8")
        (bad / "plugin.yaml").write_text(
            yaml.replace("community.signal", "community.bad"), encoding="utf-8"
        )
        session = Session.create_default()
        host = PluginHost(toolbox_path=session.path, session=session)
        host.bind_apis()
        host.register_manifest(load_manifest(bad))
        # also load good sample
        host.register_manifest(load_manifest(SAMPLE))
        host.load_all()
        host.activate_on_startup()
        assert host.plugins["community.bad"].state.value == "faulted"
        assert host.plugins["community.signal"].state.value == "active"
        # Session still usable
        assert session.workspace.depth() == 1
        assert host.execute_command("community.signal.demo")


def test_engine_mismatch_disables(tmp_path: Path):
    root = tmp_path / "old"
    root.mkdir()
    (root / "plugin.yaml").write_text(
        """
id: community.old
version: 0.1.0
engines:
  openmatlab: ">=9.0.0"
main: extension.py
contributes:
  commands:
    - command: community.old.x
      title: X
""",
        encoding="utf-8",
    )
    (root / "extension.py").write_text("def activate(c): pass\n", encoding="utf-8")
    host = PluginHost(toolbox_path=ToolboxPath())
    host.register_manifest(load_manifest(root))
    rec = host.load_plugin("community.old")
    assert rec.state.value == "disabled"
    assert rec.engine_ok is False
    assert "requires" in (rec.error or "")


def test_extension_context_fields():
    host = _host_with_sample()
    host.bind_apis()
    host.load_all()
    host.activate_plugin("community.signal")
    ctx = host.plugins["community.signal"].context
    assert ctx is not None
    assert ctx.plugin_id == "community.signal"
    assert ctx.extension_path == SAMPLE.resolve()
    assert ctx.workspace is not None
    assert ctx.host is not None
    assert ctx.host.api_version == "0.1.0"


def test_unload_removes_contributions():
    host = _host_with_sample()
    host.bind_apis()
    host.load_all()
    host.activate_on_startup()
    assert host.slots.get("commands").by_plugin("community.signal")
    host.unload("community.signal")
    assert host.slots.get("commands").by_plugin("community.signal") == []
    assert host.plugins["community.signal"].state.value == "unloaded"


def test_path_entries_added():
    path = ToolboxPath()
    host = PluginHost(toolbox_path=path)
    host.register_manifest(load_manifest(SAMPLE))
    host.load_all()
    entries = [str(p) for p in path.list()]
    assert any("mfiles" in e for e in entries)


def test_unload_removes_path_entries():
    path = ToolboxPath()
    host = PluginHost(toolbox_path=path)
    host.register_manifest(load_manifest(SAMPLE))
    host.load_all()
    assert any("mfiles" in str(e) for e in path.list())
    host.unload("community.signal")
    assert not any("mfiles" in str(e) for e in path.list())
