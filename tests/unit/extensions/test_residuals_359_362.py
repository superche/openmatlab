"""Residuals #359–#362: builtins factory, path activation, get_extension, when."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from openmatlab.extensions.activation import (
    is_known_predicate,
    path_exists_globs,
    wants_workspace_matlab,
)
from openmatlab.extensions.host import PluginHost
from openmatlab.extensions.manifest import load_manifest
from openmatlab.extensions.when import any_matlab_files, evaluate_when, glob_matches
from openmatlab.libs.path import ToolboxPath
from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.session import Session
from openmatlab.runtime.value import Array

pytestmark = pytest.mark.unit


def _write_plugin(root: Path, yaml_body: str, extension_py: str = "") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "plugin.yaml").write_text(yaml_body, encoding="utf-8")
    if extension_py:
        (root / "extension.py").write_text(extension_py, encoding="utf-8")
    return root


# --- #359 builtins factory → FunctionResolver ---------------------------------


def test_builtins_factory_registers_into_resolver(tmp_path: Path):
    root = tmp_path / "fir"
    _write_plugin(
        root,
        """
id: community.fir
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - onStartupFinished
contributes:
  builtins:
    - name: fir1
      factory: extension:make_fir1
""",
        '''
def make_fir1():
    def _fir1(args, *, nargout=1):
        # Tiny sample: return scalar length of args as double Array
        from openmatlab.numerics.ndarray_value import NDArrayValue
        import numpy as np
        n = float(len(args))
        return (NDArrayValue(np.asarray([[n]], dtype=np.float64)),)
    return _fir1

def activate(context):
    pass
''',
    )
    resolver = FunctionResolver()
    host = PluginHost(toolbox_path=ToolboxPath(), function_resolver=resolver)
    host.bind_apis()
    host.register_manifest(load_manifest(root))
    host.load_all()
    assert "fir1" in resolver.builtins
    out = resolver.resolve("fir1")([], nargout=1)
    assert isinstance(out[0], Array)
    # unload removes builtin
    host.unload("community.fir")
    assert "fir1" not in resolver.builtins


def test_builtins_factory_with_session(tmp_path: Path):
    root = tmp_path / "tiny"
    _write_plugin(
        root,
        """
id: community.tiny
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
contributes:
  builtins:
    - name: tiny_one
      factory: extension:make_one
""",
        '''
def make_one():
    def _one(args, *, nargout=1):
        from openmatlab.numerics.ndarray_value import NDArrayValue
        import numpy as np
        return (NDArrayValue(np.asarray([[1.0]], dtype=np.float64)),)
    return _one
''',
    )
    session = Session.create_default()
    host = PluginHost(toolbox_path=session.path, session=session)
    host.register_manifest(load_manifest(root))
    host.load_all()
    assert "tiny_one" in session.functions.builtins
    vals = session.functions.resolve("tiny_one")([])
    assert float(vals[0].backend_buffer().reshape(-1)[0]) == 1.0


# --- #360 path / workspace activation ----------------------------------------


def test_on_path_exists_activates(tmp_path: Path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "probe.m").write_text("% probe\n", encoding="utf-8")
    root = tmp_path / "pathplug"
    _write_plugin(
        root,
        """
id: community.pathy
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - onPathExists:probe.m
contributes:
  commands:
    - command: community.pathy.go
      title: Go
""",
        '''
def activate(context):
    context.host.commands.register_command(
        "community.pathy.go", lambda: "path-ok"
    )
''',
    )
    monkeypatch.chdir(ws)
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    host.register_manifest(load_manifest(root))
    host.load_all()
    assert host.plugins["community.pathy"].state.value == "loaded"
    # startup alone should not activate (no onStartupFinished)
    host.activate_on_startup()
    assert host.plugins["community.pathy"].state.value == "active"
    assert host.execute_command("community.pathy.go") == "path-ok"


def test_workspace_has_matlab_files_activates(tmp_path: Path, monkeypatch):
    ws = tmp_path / "matlab_ws"
    ws.mkdir()
    (ws / "hello.m").write_text("function hello()\nend\n", encoding="utf-8")
    root = tmp_path / "wplug"
    _write_plugin(
        root,
        """
id: community.wsm
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - workspaceHasMatlabFiles
""",
        "def activate(context):\n    pass\n",
    )
    monkeypatch.chdir(ws)
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    host.register_manifest(load_manifest(root))
    host.load_all()
    activated = host.poll_path_activation()
    assert "community.wsm" in activated
    assert host.plugins["community.wsm"].state.value == "active"


def test_unknown_predicate_warns_and_stays_inactive(tmp_path: Path, caplog):
    root = tmp_path / "unk"
    _write_plugin(
        root,
        """
id: community.unk
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - onAlienEvent
""",
        "def activate(context):\n    pass\n",
    )
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    host.register_manifest(load_manifest(root))
    host.load_all()
    with caplog.at_level(logging.WARNING, logger="openmatlab.extensions"):
        host.activate_on_startup()
        host.poll_path_activation()
    assert host.plugins["community.unk"].state.value == "loaded"
    assert any("unknown activation predicate" in r.message for r in caplog.records)


def test_path_helpers():
    assert path_exists_globs(["onPathExists:*.m", "onStartupFinished"]) == ["*.m"]
    assert wants_workspace_matlab(["workspaceHasMatlabFiles"]) is True
    assert is_known_predicate("onPathExists:foo") is True
    assert is_known_predicate("onAlien") is False


# --- #361 get_extension -------------------------------------------------------


def test_get_extension_active_exports(tmp_path: Path):
    root = tmp_path / "exp"
    _write_plugin(
        root,
        """
id: community.exp
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - onStartupFinished
""",
        '''
exports = {"answer": 42}

def activate(context):
    pass
''',
    )
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    host.register_manifest(load_manifest(root))
    host.load_all()
    host.activate_on_startup()
    info = host.get_extension("community.exp")
    assert info.id == "community.exp"
    assert info.is_active is True
    assert info.state == "active"
    assert info.exports["answer"] == 42
    # module-level API
    from openmatlab.extensions import extensions as ext_api

    info2 = ext_api.get_extension("community.exp")
    assert info2.exports["answer"] == 42


def test_get_extension_missing_id():
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    with pytest.raises(KeyError, match="unknown extension"):
        host.get_extension("does.not.exist")


def test_get_extension_faulted_flagged(tmp_path: Path):
    root = tmp_path / "boom"
    _write_plugin(
        root,
        """
id: community.boom
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - onStartupFinished
""",
        "def activate(context):\n    raise RuntimeError('boom')\n",
    )
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    host.register_manifest(load_manifest(root))
    host.load_all()
    host.activate_on_startup()
    info = host.get_extension("community.boom")
    assert info.is_active is False
    assert info.state == "faulted"
    assert info.error and "boom" in info.error


# --- #362 when clauses --------------------------------------------------------


def test_evaluate_when_subset(tmp_path: Path, caplog):
    assert evaluate_when(None, has_matlab_files=False) is True
    assert evaluate_when("", has_matlab_files=False) is True
    assert evaluate_when("true", has_matlab_files=False) is True
    assert evaluate_when("false", has_matlab_files=True) is False
    assert evaluate_when("workspaceHasMatlabFiles", has_matlab_files=True) is True
    assert evaluate_when("workspaceHasMatlabFiles", has_matlab_files=False) is False
    with caplog.at_level(logging.WARNING, logger="openmatlab.extensions"):
        assert evaluate_when("unknownThing", has_matlab_files=True) is False
    assert any("unknown when clause" in r.message for r in caplog.records)


def test_list_menus_and_panels_respect_when(tmp_path: Path, monkeypatch):
    ws = tmp_path / "empty_ws"
    ws.mkdir()
    root = tmp_path / "whenplug"
    _write_plugin(
        root,
        """
id: community.when
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
main: extension.py
activation:
  - onStartupFinished
contributes:
  menus:
    - path: Tools/Always
      command: community.when.a
    - path: Tools/MatlabOnly
      command: community.when.b
      when: workspaceHasMatlabFiles
    - path: Tools/Never
      command: community.when.c
      when: false
  panels:
    - id: community.when.panel
      title: WhenPanel
      when: workspaceHasMatlabFiles
""",
        "def activate(context):\n    pass\n",
    )
    monkeypatch.chdir(ws)
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    host.register_manifest(load_manifest(root))
    host.load_all()
    menus = host.list_menus()
    paths = [m["path"] for m in menus if isinstance(m, dict)]
    assert "Tools/Always" in paths
    assert "Tools/Never" not in paths
    assert "Tools/MatlabOnly" not in paths  # no .m in empty cwd
    assert host.list_panel_contributions() == []

    # Add a .m and re-evaluate
    (ws / "x.m").write_text("% x\n", encoding="utf-8")
    menus2 = host.list_menus()
    paths2 = [m["path"] for m in menus2 if isinstance(m, dict)]
    assert "Tools/MatlabOnly" in paths2
    panels = host.list_panel_contributions()
    assert any(
        isinstance(p, dict) and p.get("id") == "community.when.panel" for p in panels
    )


def test_glob_and_matlab_helpers(tmp_path: Path):
    d = tmp_path / "g"
    d.mkdir()
    (d / "a.m").write_text("%a\n", encoding="utf-8")
    assert any_matlab_files([d]) is True
    assert glob_matches([d], "*.m") is True
    assert glob_matches([d], "missing.txt") is False
