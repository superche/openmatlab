"""Joins and grouping (Epic #696, M10 T06/T07)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

AB = ("A = table([1;2;3], [10;20;30], 'VariableNames', {'k','x'}); "
      "B = table([3;1;4], [300;100;400], 'VariableNames', {'k','y'}); ")


def run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def num(code, name="v"):
    return np.asarray(run(code).workspace.get(name).backend_buffer(), float).tolist()


def names(code, name="v"):
    return [c.text for c in run(code).workspace.get(name).rows[0]]


def test_innerjoin_sorted_by_key_with_indices():
    assert num(AB + "[I, ia, ib] = innerjoin(A, B); v = [I.k I.x I.y ia ib];") == [[1, 10, 100, 1, 2], [3, 30, 300, 3, 1]]
    assert num("A = table({'a';'b'}, [1;2], 'VariableNames', {'k','x'}); B = table({'b';'b'}, [5;6], 'VariableNames', {'k','y'}); "
               "I = innerjoin(A, B); v = I.y';") == [[5, 6]]


def test_outerjoin_types_and_mergekeys():
    assert num(AB + "O = outerjoin(A, B, 'MergeKeys', true); v = O.k';") == [[1, 2, 3, 4]]
    assert num(AB + "O = outerjoin(A, B, 'Type', 'left', 'MergeKeys', true); v = height(O);") == [[3]]
    assert num(AB + "O = outerjoin(A, B, 'Type', 'right', 'MergeKeys', true); v = O.k';") == [[1, 3, 4]]
    assert names(AB + "O = outerjoin(A, B); v = O.Properties.VariableNames;") == ["k_A", "x", "k_B", "y"]
    assert num(AB + "[O, ia, ib] = outerjoin(A, B, 'MergeKeys', true); v = [ia ib];") == [[1, 2], [2, 0], [3, 1], [0, 3]]


def test_outerjoin_fills_each_type_with_its_missing_value():
    s = run("A = table([1;2], int8([3;4]), [true;false], categorical({'p';'q'}), datetime(2020,1,[1;2]), [\"s1\";\"s2\"], "
            "{'u';'w'}, 'VariableNames', {'k','i','l','c','d','s','t'}); B = table([2;9], 'VariableNames', {'k'}); "
            "O = outerjoin(A, B, 'MergeKeys', true); v = [double(O.i(3)) double(O.l(3)) isundefined(O.c(3)) isnat(O.d(3)) "
            "ismissing(O.s(3)) isempty(O.t{3})];")
    assert np.asarray(s.workspace.get("v").backend_buffer(), float).tolist() == [[0, 0, 1, 1, 1, 1]]


def test_join_keeps_left_order_and_requires_matches():
    assert num(AB + "C = table([3;1;2], [9;7;8], 'VariableNames', {'k','z'}); J = join(A, C); v = [J.z' width(J)];") == [[7, 8, 9, 3]]
    assert num("A = table([1;2], [3;4], 'VariableNames', {'k','x'}); B = table([2;5], [7;8], 'VariableNames', {'kk','y'}); "
               "O = outerjoin(A, B, 'LeftKeys', 'k', 'RightKeys', 'kk', 'Type', 'right'); v = O.y';") == [[7, 8]]


def test_findgroups_and_splitapply():
    assert num("v = findgroups([3 1 3]);") == [[2, 1, 2]]
    assert num("[G, ID] = findgroups([1;NaN;2]); v = [isnan(G') ID'];") == [[0, 1, 0, 1, 2]]
    assert num("[G, a, b] = findgroups([1;1;2], {'x';'y';'x'}); v = G';") == [[1, 2, 3]]
    assert num("v = splitapply(@max, [1;5;3;2], findgroups({'a';'a';'b';'b'}))';") == [[5, 3]]


def test_groupsummary_and_groupcounts():
    base = "T = table([1;2;1;2;3], [10;20;30;40;50], 'VariableNames', {'g','x'}); "
    assert num(base + "S = groupsummary(T, 'g', {'mean','range'}, 'x'); v = [S.mean_x S.range_x S.GroupCount];") == [
        [20, 20, 2], [30, 20, 2], [50, 0, 1]]
    assert num(base + "S = groupsummary(T, 'g'); v = width(S);") == [[2]]
    assert num(base + "S = groupsummary(T, 'g', @(x) max(x) - min(x), 'x'); v = S.fun1_x';") == [[20, 20, 0]]
    assert num("T = table([1;NaN;1], [4;5;6]); S = groupsummary(T, 'Var1', 'sum'); v = S.sum_Var2';") == [[10, 5]]
    assert num("T = table([1;NaN;1], [4;5;6]); S = groupsummary(T, 'Var1', 'sum', 'IncludeMissingGroups', false); v = height(S);") == [[1]]
    assert num(base + "C = groupcounts(T, 'g'); v = [C.GroupCount C.Percent];") == [[2, 40], [2, 40], [1, 20]]


@pytest.mark.parametrize("code", [
    AB + "join(A, B)",
    "A = table([1;2],'VariableNames',{'k'}); B = table([1;1],[3;4],'VariableNames',{'k','v'}); join(A, B)",
    "A = table([1;2],'VariableNames',{'k'}); B = table({'1';'2'},'VariableNames',{'k'}); innerjoin(A, B)",
    "A = table([1;2],'VariableNames',{'k'}); B = table([1;2],'VariableNames',{'z'}); innerjoin(A, B)",
    "innerjoin(table(1), 5)",
    AB + "outerjoin(A, B, 'Type', 'sideways')",
    AB + "outerjoin(A, B, 'Keys', 'k', 'LeftKeys', 'k')",
    AB + "innerjoin(A, B, 'LeftKeys', 'k')",
    "findgroups([1;2], [1;2;3])",
    "splitapply(@sum, [1;2;3], [1;3;1])",
    "splitapply(@(x) x, [1;2;3], [1;1;2])",
    "splitapply(5, [1;2], [1;2])",
    "splitapply(@sum, [1;2], [0;1])",
    "splitapply(@sum, [1;2;3], [1;2])",
    "groupsummary(table([1;1;2],[4;5;6]), 'Var1', 'banana')",
    "groupsummary(table([1;1;2],{'a';'b';'c'}), 'Var1', 'mean', 'Var2')",
    "groupsummary(5, 'x', 'sum')",
    "groupsummary(table([1;1;2],[4;5;6]), 'Var1', 'sum', 'Var2', 'IncludeEmptyGroups', true)",
    "groupcounts(table([1;2]), 'nope')",
])
def test_errors_are_matlab_errors(code):
    with pytest.raises(EvalError):
        run(code)
