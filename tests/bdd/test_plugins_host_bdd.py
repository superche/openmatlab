"""BDD smoke for plugin host (pytest-bdd)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.extensions.host import PluginHost
from openmatlab.extensions.manifest import load_manifest
from openmatlab.libs.path import ToolboxPath

pytestmark = [pytest.mark.bdd, pytest.mark.unit]

scenarios("../../features/plugins_host.feature")

SAMPLE = Path("demos/plugins/community.signal")


@given("the community.signal sample plugin is discovered", target_fixture="plugin_host")
def discover_sample():
    host = PluginHost(toolbox_path=ToolboxPath())
    host.bind_apis()
    host.register_manifest(load_manifest(SAMPLE))
    host.load_all()
    return host


@when("the plugin host activates on startup")
def activate_startup(plugin_host: PluginHost):
    plugin_host.activate_on_startup()


@when(parsers.parse('I execute the command "{command_id}"'), target_fixture="command_result")
def execute_cmd(plugin_host: PluginHost, command_id: str):
    return plugin_host.execute_command(command_id)


@then(parsers.parse('the command result contains "{snippet}"'))
def result_contains(command_result: str, snippet: str):
    assert snippet in command_result


@then(parsers.parse('the plugin state is "{state}"'))
def plugin_state(plugin_host: PluginHost, state: str):
    assert plugin_host.plugins["community.signal"].state.value == state


@given(
    "a sample plugin with contributes.builtins factory",
    target_fixture="plugin_host_builtins",
)
def discover_builtins_plugin(tmp_path):
    root = tmp_path / "fir_bdd"
    root.mkdir()
    (root / "plugin.yaml").write_text(
        """
id: community.fir_bdd
version: 0.1.0
engines:
  openmatlab: ">=0.1.0 <0.2.0"
contributes:
  builtins:
    - name: fir1
      factory: extension:make_fir1
""",
        encoding="utf-8",
    )
    (root / "extension.py").write_text(
        '''
def make_fir1():
    def _fir1(args, *, nargout=1):
        from openmatlab.numerics.ndarray_value import NDArrayValue
        import numpy as np
        return (NDArrayValue(np.asarray([[0.0]], dtype=np.float64)),)
    return _fir1
''',
        encoding="utf-8",
    )
    from openmatlab.runtime.functions import FunctionResolver

    resolver = FunctionResolver()
    host = PluginHost(toolbox_path=ToolboxPath(), function_resolver=resolver)
    host.bind_apis()
    host.register_manifest(load_manifest(root))
    host._test_resolver = resolver  # type: ignore[attr-defined]
    return host


@when("the plugin host loads the plugin")
def load_plugin_step(plugin_host_builtins: PluginHost):
    plugin_host_builtins.load_all()


@then(parsers.parse('the FunctionResolver has builtin "{name}"'))
def resolver_has_builtin(plugin_host_builtins: PluginHost, name: str):
    resolver = plugin_host_builtins._test_resolver  # type: ignore[attr-defined]
    assert name.lower() in resolver.builtins
