"""BDD smoke for MATLAB-aligned Workbench (pytest-bdd)."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]

scenarios("../../features/workbench.feature")


@given("a fresh workbench", target_fixture="workbench")
def fresh_workbench():
    return Workbench.create()


@when("I list workbench regions", target_fixture="region_list")
def list_regions(workbench: Workbench):
    return workbench.regions()


@then(parsers.parse('the region list includes "{region_id}"'))
def region_includes(region_list, region_id: str):
    assert region_id in [r.id for r in region_list]


@then(parsers.parse('the region "{region_id}" status is "{status}"'))
def region_status(region_list, region_id: str, status: str):
    by_id = {r.id: r for r in region_list}
    assert by_id[region_id].status == status


@when(
    parsers.parse('I evaluate "{code}" in the command window'),
    target_fixture="cw_output",
)
def eval_cw(workbench: Workbench, code: str):
    return workbench.command_window.eval(code)


@then(parsers.parse('the command window output contains "{snippet}"'))
def cw_contains(cw_output: str, snippet: str):
    assert snippet in cw_output


@then(parsers.parse('the workspace contains "{name}"'))
def ws_contains(workbench: Workbench, name: str):
    assert name in workbench.command_window.workspace_names()
