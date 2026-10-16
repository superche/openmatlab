"""Table utilities, sorting and sets (Epic #693, M10 T03/T05)."""

from __future__ import annotations

import io
from contextlib import redirect_stdout

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

T3 = "T = table([1;2;3], [4;5;6], 'VariableNames', {'a','b'}); "


def run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def num(code, name="v"):
    return np.asarray(run(code).workspace.get(name).backend_buffer(), float).tolist()


def test_conversions():
    assert num(T3 + "v = table2array(T);") == [[1, 4], [2, 5], [3, 6]]
    assert num("T = table([1;2],[3 4;5 6]); v = table2array(T);") == [[1, 3, 4], [2, 5, 6]]
    assert num("T = table([1;2],{'x';'yy'}); C = table2cell(T); v = [C{2,1} numel(C{2,2})];") == [[2, 2]]
    assert num(T3 + "s = table2struct(T); v = [numel(s) s(2).b];") == [[3, 5]]
    assert num(T3 + "s = table2struct(T, 'ToScalar', true); v = s.b';") == [[4, 5, 6]]


def test_head_tail():
    assert num("T = table((1:10)'); v = height(head(T));") == [[8]]
    assert num("T = table((1:10)'); L = tail(T, 3); v = L.Var1';") == [[8, 9, 10]]
    assert num("v = head([5;6;7], 2);") == [[5], [6]]
    assert num(T3 + "v = height(head(T, 10));") == [[3]]


def test_varfun_rowfun():
    assert num(T3 + "V = varfun(@sum, T); v = [V.sum_a V.sum_b];") == [[6, 15]]
    assert num(T3 + "v = varfun(@mean, T, 'OutputFormat', 'uniform');") == [[2, 5]]
    assert num(T3 + "V = varfun(@(x) x*2, T, 'InputVariables', 'b'); v = V.Fun_b';") == [[8, 10, 12]]
    assert num(T3 + "R = rowfun(@(x, y) x + y, T); v = R.Var1';") == [[5, 7, 9]]
    assert num(T3 + "v = rowfun(@(x, y) x * y, T, 'OutputFormat', 'uniform')';") == [[4, 10, 18]]
    assert num(T3 + "R = rowfun(@(x) -x, T, 'InputVariables', 'a', 'OutputVariableNames', 'neg'); v = R.neg';") == [[-1, -2, -3]]


def test_variable_management():
    assert num(T3 + "v = width(removevars(T, 'a'));") == [[1]]
    assert num(T3 + "U = renamevars(T, {'a','b'}, {'x','y'}); v = U.y';") == [[4, 5, 6]]
    s = run("T = table(1,2,3); U = movevars(T, {'Var1','Var2'}, 'After', 'Var3'); n = U.Properties.VariableNames;")
    assert [c.text for c in s.workspace.get("n").rows[0]] == ["Var3", "Var1", "Var2"]
    s = run(T3 + "z = [7;8;9]; U = addvars(T, z, 'Before', 'b'); n = U.Properties.VariableNames;")
    assert [c.text for c in s.workspace.get("n").rows[0]] == ["a", "z", "b"]


def test_summary_prints_stats():
    s = Session.create_default()
    buf = io.StringIO()
    with redirect_stdout(buf):
        ReplSession(s).run_line("T = table([1;2;NaN], categorical({'p';'q';'p'}), 'VariableNames', {'n','c'}); summary(T)")
    out = buf.getvalue()
    assert "n: 3×1 double" in out and "Median" in out and "NumMissing" in out
    assert "c: 3×1 categorical" in out


def test_sortrows_tables():
    base = "T = table([3;1;2;1], {'c';'a';'b';'d'}, 'VariableNames', {'n','s'}); "
    assert num(base + "S = sortrows(T, 'n'); v = S.n';") == [[1, 1, 2, 3]]
    assert num(base + "[S, i] = sortrows(T, {'n','s'}, {'ascend','descend'}); v = i';") == [[4, 2, 3, 1]]
    assert num(base + "S = sortrows(T, -1); v = S.n';") == [[3, 2, 1, 1]]
    assert num("T = table([2;NaN;1]); S = sortrows(T); v = S.Var1';")[0][:2] == [1, 2]
    assert np.isnan(num("T = table([2;NaN;1]); S = sortrows(T, 'descend'); v = S.Var1';")[0][0])
    assert num("T = table([2;1;3], 'RowNames', {'b','a','c'}); S = sortrows(T, 'RowNames'); v = S.Var1';") == [[1, 2, 3]]
    assert num("T = table(categorical({'z';'y'}), datetime(2020,1,[2;1])); S = sortrows(T, 2); v = S.Var2.Day';") == [[1, 2]]
    assert num(base + "v = [issortedrows(sortrows(T, 'n'), 'n') issortedrows(T, 'n')];") == [[1, 0]]


def test_sets():
    assert num("[C, ia, ic] = unique(table([1;1;2], {'a';'a';'b'})); v = [height(C) ia' ic'];") == [[2, 1, 3, 1, 1, 2]]
    assert num("[tf, loc] = ismember(table([2;9], [6;0]), table([1;2], [5;6])); v = [tf loc];") == [[1, 2], [0, 0]]
    assert num("c = categorical({'b','a','b'}); [s, i] = sort(c, 'descend'); v = i;") == [[1, 3, 2]]
    assert num("[tf, loc] = ismember(categorical({'b','q'}), categorical({'a','b'})); v = [tf loc];") == [[1, 0, 2, 0]]


@pytest.mark.parametrize("code", [
    "table2array(table([1;2], {'a';'b'}))",
    "table2array(5)",
    "head(table(1), -1)",
    T3 + "varfun(@(x) x, T, 'OutputFormat', 'uniform')",
    T3 + "varfun(5, T)",
    T3 + "varfun(@sum, T, 'GroupingVariables', 'a')",
    T3 + "rowfun(@(x) x, T, 'OutputFormat', 'banana')",
    T3 + "removevars(T, 'nope')",
    T3 + "renamevars(T, {'a','b'}, {'x'})",
    T3 + "renamevars(T, 'a', 'b')",
    T3 + "movevars(T, 'a', 'Before', 'b', 'After', 'b')",
    T3 + "addvars(T, [1;2])",
    T3 + "sortrows(T, 'a', 'sideways')",
    "sortrows(table({1;2}))",
    "sortrows(table([1;2]), 'RowNames')",
    "unique(table([1;2]), 'stable')",
    "ismember(table(1), 5)",
    "ismember(table(1,2), table(1,2,'VariableNames',{'x','y'}))",
    "ismember(categorical({'b'}), 5)",
    "sort(categorical({'b'}), 'sideways')",
])
def test_errors_are_matlab_errors(code):
    with pytest.raises(EvalError):
        run(code)
