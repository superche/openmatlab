"""BDD smoke for MATLAB-aligned Workbench (pytest-bdd)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.bdd, pytest.mark.unit, pytest.mark.needs_numpy]

scenarios("../../features/workbench.feature")


@given("a fresh workbench", target_fixture="workbench")
def fresh_workbench(tmp_path: Path):
    return Workbench.create(cwd=tmp_path)


@given(
    parsers.parse('a temporary m-file "{name}" with contents "{body}"'),
    target_fixture="tmp_mfile",
)
def make_tmp_mfile(workbench: Workbench, name: str, body: str):
    path = workbench.current_folder.pwd() / name
    path.write_text(body, encoding="utf-8")
    return path


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


@when("I refresh the workspace browser", target_fixture="ws_rows")
def refresh_ws(workbench: Workbench):
    return workbench.workspace_browser.refresh()


@then(parsers.parse('the workspace browser lists "{name}" with class "{cls}"'))
def ws_row_class(ws_rows, name: str, cls: str):
    by_name = {r.name: r for r in ws_rows}
    assert name in by_name
    assert by_name[name].matlab_class == cls


@when("I open the temporary m-file in the editor")
def open_tmp_mfile(workbench: Workbench, tmp_mfile: Path):
    workbench.editor.open_file(tmp_mfile)


@when(parsers.parse('I set the editor text to "{body}"'))
def set_editor_text(workbench: Workbench, body: str):
    workbench.editor.set_text(body)


@when(parsers.parse('I save the editor to a new temporary path "{name}"'))
def save_editor(workbench: Workbench, name: str):
    target = workbench.current_folder.pwd() / name
    workbench.editor.save(target)


@then(parsers.parse('the temporary file "{name}" contains "{snippet}"'))
def tmp_file_contains(workbench: Workbench, name: str, snippet: str):
    text = (workbench.current_folder.pwd() / name).read_text(encoding="utf-8")
    assert snippet in text
