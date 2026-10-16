from __future__ import annotations

import pytest

from openmatlab.host.variable_editor import VariableEditError
from openmatlab.host.workbench import Workbench

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture
def wb(tmp_path):
    w = Workbench.create(cwd=tmp_path)
    w.eval("A = [1 2; 3 4]; s = 'hi'; c = {1, 'x'}; st.a = 5; st.b = 'q'; T = table([1;2], [3;4]); z = zeros(2,2,2);")
    return w


def test_numeric_read_edit_grow(wb):
    v = wb.variable_editor.open("A")
    assert v.size() == (2, 2) and v.grid() == [["1", "2"], ["3", "4"]]
    v.set_cell(3, 3, "9")
    assert v.size() == (3, 3) and v.cell(3, 1) == "0"


def test_nd_folds_pages(wb):
    v = wb.variable_editor.open("z")
    assert v.size() == (2, 4)
    v.set_cell(2, 4, "5")
    assert wb.eval_value("z(2,2,2)") == 5


def test_char_literal_character(wb):
    v = wb.variable_editor.open("s")
    v.set_cell(1, 2, "q")
    assert wb.eval_value("s") == "hq"
    with pytest.raises(VariableEditError):
        v.set_cell(1, 1, "'ab'")


def test_cell_struct_table(wb):
    ve = wb.variable_editor
    assert ve.open("c").cell(1, 2) == "'x'"
    ve.open("c").set_cell(1, 1, "[1 2 3]")
    assert ve.open("c").cell(1, 1) == "[1 2 3]"
    vs = ve.open("st")
    assert vs.row_headers() == ["a", "b"] and vs.column_headers() == ["Field", "Value"]
    with pytest.raises(VariableEditError):
        vs.set_cell(1, 1, "3")
    vt = ve.open("T")
    vt.set_cell(2, 1, "20")
    assert wb.eval_value("T.Var1(2)") == 20


@pytest.mark.parametrize("text", ["1+", "x = 3", "undefinedfoo", "{1}", ""])
def test_bad_edit_unchanged(wb, text):
    v = wb.variable_editor.open("A")
    with pytest.raises(VariableEditError):
        v.set_cell(1, 1, text)
    assert wb.eval_value("A(1,1)") == 1


def test_bad_position_and_missing(wb):
    with pytest.raises(VariableEditError):
        wb.variable_editor.open("A").set_cell(0, 1, "1")
    with pytest.raises(VariableEditError):
        wb.variable_editor.open("nope")


def test_edit_not_in_history_and_region(wb):
    before = list(wb.command_window.history())
    wb.variable_editor.open("A").set_cell(1, 1, "7")
    assert list(wb.command_window.history()) == before
    assert "Variables" in [r.title for r in wb.regions()]
