"""table core: construction, Properties, indexing, assignment, concatenation, display (Epic #691)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture
def run():
    s = Session.create_default()
    r = ReplSession(s)

    def go(code):
        r.run_line(code)
        return s

    return go


def _num(s, name):
    return np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def test_names_from_variables_and_default(run):
    s = run("x = [1;2]; y = {'a';'b'}; T = table(x, y, [5;6]); n = T.Properties.VariableNames; k = numel(n);")
    names = [c.text for c in s.workspace.get("n").rows[0]]
    assert names == ["x", "y", "Var3"]


def test_display_layout(run):
    out = run("Name = {'Ann';'Bob'}; Age = [31;45]; T = table(Name, Age); out = evalc('T');").workspace.get("out").text
    assert "2×2 table" in out
    assert "Name" in out and "Age" in out and "{'Ann'}" in out and "45" in out


def test_disp_has_no_size_line(run):
    out = run("T = table([1;2], 'VariableNames', {'p'}); out = evalc('disp(T)');").workspace.get("out").text
    assert "table" not in out and "p" in out


def test_row_names_and_properties(run):
    s = run("T = table([10;20], 'RowNames', {'r1','r2'}); a = T{'r2', 1}; T.Properties.RowNames = {'x','y'};"
            " b = T{'x', 'Var1'}; T.Properties.VariableNames = {'v'}; c = T.v(2);")
    assert _num(s, "a") == [20] and _num(s, "b") == [10] and _num(s, "c") == [20]


def test_nested_chains_and_colon(run):
    s = run("T = table([1 2; 3 4], {'a';'b'}); a = T.Var1(:, 2)'; T.Var2{2} = 'z'; b = double(T.Var2{2});"
            " T.Var1(:) = 0; c = sum(T.Var1(:));")
    assert _num(s, "a") == [2, 4] and _num(s, "b") == [ord("z")] and _num(s, "c") == [0]


def test_grow_rows_with_cell(run):
    s = run("T = table({'a';'b'}, [1;2]); T(3,:) = {'c', 3}; h = height(T); v = T.Var2';")
    assert _num(s, "h") == [3] and _num(s, "v") == [1, 2, 3]


def test_table_in_struct_and_cell(run):
    s = run("s.t = table([1;2]); s.t.Var1(2) = 5; a = s.t.Var1'; c = {table([1;2])}; c{1}.Var1(1) = 7; b = c{1}.Var1';")
    assert _num(s, "a") == [1, 5] and _num(s, "b") == [7, 2]


def test_scalar_expansion_and_delete(run):
    s = run("T = table([1;2;3]); T.k = 7; a = T.k'; T(:, 'k') = []; w = width(T); T([1 3], :) = []; h = height(T);")
    assert _num(s, "a") == [7, 7, 7] and _num(s, "w") == [1] and _num(s, "h") == [1]


def test_isempty_size_class(run):
    s = run("E = table(); e = isempty(E); T = table([1;2],[3;4]); z = size(T); n = numel(T); c = strcmp(class(T), 'table');")
    assert _num(s, "e") == [1] and _num(s, "z") == [2, 2] and _num(s, "n") == [4] and _num(s, "c") == [1]


def test_datetime_column(run):
    s = run("d = datetime(2020,1,1) + days([0;1]); T = table(d, [1;2]); y = T.d(2).Day;")
    assert _num(s, "y") == [2]


@pytest.mark.parametrize("code,msg", [
    ("T = table([1;2]); T.zz", "Unrecognized table variable name 'zz'"),
    ("T = table([1;2]); T(5, 1)", "Row index exceeds table dimensions"),
    ("T = table([1;2]); T(1)", "linear indexing"),
    ("T = table([1;2]); T.y = [1;2;3];", "number of rows must match"),
    ("table([1;2], [1;2;3])", "same number of rows"),
    ("table([1;2], 'VariableNames', {'a','b'})", "one name for each variable"),
    ("T = table([1;2]); [T; table(3, 'VariableNames', {'x'})]", "same variable names"),
    ("T = table([1;2]); [T T]", "Duplicate table variable name"),
    ("T = table([1;2]); -T", "type 'table'"),
    ("T = table([1;2]); T + 1", "not supported for operands of type 'table'"),
    ("T = table([1;2]); T(1, 1) = [];", "colon"),
    ("table([1;2], 'VariableNames', {'Properties'})", "reserved"),
])
def test_errors_are_matlab_errors(run, code, msg):
    with pytest.raises(EvalError, match=msg):
        run(code)
