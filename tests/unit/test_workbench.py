"""Workbench Host product — W01 layout + W02 Command Window."""

from __future__ import annotations

import pytest

from openmatlab.host.cli import main
from openmatlab.host.workbench import HOST_REGIONS, CommandWindow, Workbench

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_host_regions_named():
    assert HOST_REGIONS == (
        "command_window",
        "editor",
        "workspace_browser",
        "current_folder",
        "figures",
    )


def test_workbench_list_regions_includes_host_stubs():
    wb = Workbench.create()
    ids = [r.id for r in wb.regions()]
    for hid in HOST_REGIONS:
        assert hid in ids
    by_id = {r.id: r for r in wb.regions()}
    assert by_id["command_window"].status == "ready"
    assert by_id["editor"].status == "stub"
    assert by_id["command_window"].kind == "host"


def test_command_window_eval_and_workspace():
    cw = CommandWindow.create()
    text = cw.eval("a = [1 2 3];")
    assert text == ""
    text2 = cw.eval("b = a + 1")
    assert "b =" in text2 or "2" in text2
    names = cw.workspace_names()
    assert "a" in names
    assert "b" in names


def test_cli_workbench_list_only(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["workbench", "--list-only"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "command_window" in out
    assert "Command Window" in out
    assert "stub" in out


def test_cli_workbench_eval(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["workbench", "--eval", "x = 1+1"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "x =" in out or "2" in out
