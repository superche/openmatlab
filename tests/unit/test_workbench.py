"""Workbench Host product — W01–W06 layout + panels."""

from __future__ import annotations

from pathlib import Path

import pytest

from openmatlab.host.cli import main
from openmatlab.host.workbench import (
    HOST_REGIONS,
    CommandWindow,
    CurrentFolderBrowser,
    EditorPanel,
    Workbench,
)

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def test_host_regions_named():
    assert HOST_REGIONS == (
        "command_window",
        "editor",
        "workspace_browser",
        "current_folder",
        "figures",
    )


def test_workbench_list_regions_all_ready():
    wb = Workbench.create()
    ids = [r.id for r in wb.regions()]
    for hid in HOST_REGIONS:
        assert hid in ids
    by_id = {r.id: r for r in wb.regions()}
    assert by_id["command_window"].status == "ready"
    assert by_id["editor"].status == "ready"
    assert by_id["workspace_browser"].status == "ready"
    assert by_id["current_folder"].status == "ready"
    assert by_id["figures"].status == "ready"
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


def test_editor_open_edit_save(tmp_path: Path):
    src = tmp_path / "hello.m"
    src.write_text("x = 1;\n", encoding="utf-8")
    ed = EditorPanel()
    content = ed.open_file(src)
    assert content == "x = 1;\n"
    assert ed.path == src.resolve()
    assert ed.dirty is False
    ed.set_text("x = 2;\n")
    assert ed.dirty is True
    out = tmp_path / "out.m"
    saved = ed.save(out)
    assert saved == out.resolve()
    assert out.read_text(encoding="utf-8") == "x = 2;\n"
    assert ed.dirty is False


def test_editor_save_requires_path():
    ed = EditorPanel()
    ed.set_text("a=1;")
    with pytest.raises(ValueError, match="no path"):
        ed.save()


def test_workspace_browser_name_size_class():
    wb = Workbench.create()
    wb.eval("v = [1 2 3 4];")
    wb.eval("c = 'hi';")
    rows = {r.name: r for r in wb.workspace_browser.refresh()}
    assert "v" in rows
    assert rows["v"].size == "1x4"
    assert rows["v"].matlab_class == "double"
    assert "c" in rows
    assert rows["c"].matlab_class == "char"
    assert "1x2" in rows["c"].size
    table = wb.workspace_browser.as_table()
    assert "v" in table and "double" in table


def test_current_folder_list_cd_open_m(tmp_path: Path):
    sub = tmp_path / "proj"
    sub.mkdir()
    mfile = sub / "script.m"
    mfile.write_text("y = 42;\n", encoding="utf-8")
    (sub / "readme.txt").write_text("x", encoding="utf-8")

    wb = Workbench.create(cwd=tmp_path)
    assert wb.current_folder.pwd() == tmp_path.resolve()
    names = {e.name: e for e in wb.current_folder.list_entries()}
    assert "proj" in names and names["proj"].kind == "dir"

    wb.current_folder.cd("proj")
    assert wb.current_folder.pwd() == sub.resolve()
    entries = {e.name: e for e in wb.current_folder.list_entries()}
    assert entries["script.m"].is_mfile is True
    assert entries["readme.txt"].is_mfile is False

    text = wb.current_folder.open_mfile("script.m", wb.editor)
    assert "42" in text
    assert wb.editor.path == mfile.resolve()


def test_figure_manager_list_close_focus():
    pytest.importorskip("matplotlib")
    wb = Workbench.create()
    assert wb.figures.list_figures() == []
    wb.eval("plot(1:5);")
    figs = wb.figures.list_figures()
    assert len(figs) == 1
    assert figs[0].handle == 1.0
    assert "Figure" in figs[0].title
    wb.eval("plot(1:3);")
    assert len(wb.figures.list_figures()) == 2
    wb.figures.focus(1.0)
    wb.figures.close(1.0)
    remaining = wb.figures.list_figures()
    assert len(remaining) == 1
    assert remaining[0].handle == 2.0
    wb.figures.close()
    assert wb.figures.list_figures() == []


def test_cli_workbench_list_only(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["workbench", "--list-only"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "command_window" in out
    assert "Command Window" in out
    assert "editor" in out
    assert "workspace_browser" in out
    assert "current_folder" in out
    assert "figures" in out
    # All host regions ready (W01–W06)
    for line in out.splitlines():
        if any(hid in line for hid in ("command_window", "editor", "workspace_browser", "current_folder", "figures")):
            assert "ready" in line
            assert "stub" not in line


def test_cli_workbench_eval(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["workbench", "--eval", "x = 1+1"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "x =" in out or "2" in out


def test_cli_workbench_cwd(tmp_path: Path, capsys):
    with pytest.raises(SystemExit) as ei:
        main(["workbench", "--cwd", str(tmp_path), "--list-only"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "current_folder" in out


def test_menu_bar_and_toolbar_specs():
    wb = Workbench.create()
    menus = dict(wb.menu_bar())
    assert "File" in menus
    assert "Open…" in menus["File"]
    assert "Layout" in menus
    assert "New Script" in wb.toolbar()
    assert "Run" in wb.toolbar()


def test_classic_dock_layout():
    wb = Workbench.create()
    dock = wb.dock_layout()
    assert dock["current_folder"] == "left"
    assert dock["editor"] == "center"
    assert dock["command_window"] == "bottom"
    assert dock["workspace_browser"] == "right"
    assert dock["figures"] == "right"
    assert dock["menu_bar"] == "top"
    assert dock["toolstrip"] == "top"
    assert dock["path_toolbar"] == "top"
    table = wb.list_regions_table()
    assert "DOCK" in table
    assert "bottom" in table
    assert wb.apply_layout_preset("default") == "default"


def test_command_window_history():
    cw = CommandWindow.create()
    assert cw.history() == []
    cw.eval("a = 1;")
    cw.eval("b = 2")
    assert cw.history() == ["a = 1;", "b = 2"]


def test_editor_multi_document_tabs(tmp_path: Path):
    f1 = tmp_path / "one.m"
    f2 = tmp_path / "two.m"
    f1.write_text("a=1;\n", encoding="utf-8")
    f2.write_text("b=2;\n", encoding="utf-8")
    wb = Workbench.create(cwd=tmp_path)
    wb.documents.open_file(f1)
    assert wb.editor.path == f1.resolve()
    assert wb.documents.list_titles() == ["one.m"]
    wb.documents.open_file(f2)
    assert wb.editor.path == f2.resolve()
    assert wb.documents.list_titles() == ["one.m", "two.m"]
    wb.documents.switch(0)
    assert wb.editor.path == f1.resolve()
    wb.documents.close_active()
    assert wb.documents.list_titles() == ["two.m"]
    wb.documents.new_script()
    assert len(wb.documents.panels) == 2
    assert wb.editor.path is None


def test_workspace_value_column():
    wb = Workbench.create()
    wb.eval("v = [1 2 3];")
    rows = {r.name: r for r in wb.workspace_browser.refresh()}
    assert "v" in rows
    assert rows["v"].value
    assert "1" in rows["v"].value
    table = wb.workspace_browser.as_table()
    assert "Value" in table
