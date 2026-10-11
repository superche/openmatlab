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
