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


def col_texts(code, name="v"):
    return [row[0].text for row in run(code).workspace.get(name).rows]


def test_keep_one_copy_drops_the_right_duplicate():
    base = ("A = table([1;2],[10;20],[100;200],'VariableNames',{'k','x','z'}); "
            "B = table([2;1],[8;7],[9;6],'VariableNames',{'k','x','z'}); ")
    assert names(base + "J = join(A, B, 'Keys','k','KeepOneCopy','x'); v = J.Properties.VariableNames;") == [
        "k", "x", "z_A", "z_B"]
    assert num(base + "J = join(A, B, 'Keys','k','KeepOneCopy','x'); v = [J.x J.z_B];") == [[10, 6], [20, 9]]
    assert names(base + "J = join(A, B, 'Keys','k','KeepOneCopy',{'x','z'}); v = J.Properties.VariableNames;") == [
        "k", "x", "z"]
    assert num(base + "J = join(A, B, 'Keys','k','KeepOneCopy',{'x','z'}); v = [J.x J.z];") == [[10, 100], [20, 200]]
    assert names(base + "I = innerjoin(A, B, 'Keys','k','KeepOneCopy',{'x','z'}); v = I.Properties.VariableNames;") == [
        "k", "x", "z"]
    assert names(base + "O = outerjoin(A, B, 'Keys','k','KeepOneCopy','x'); v = O.Properties.VariableNames;") == [
        "k_A", "x", "z_A", "k_B", "z_B"]
    with pytest.raises(EvalError, match="KeepOneCopy' variable 'nope'"):
        run(base + "join(A, B, 'Keys','k','KeepOneCopy','nope')")


def test_keep_keys_includes_the_right_key_on_join():
    base = ("A = table([1;2],[10;20],'VariableNames',{'k','x'}); "
            "B = table([2;1],[8;7],'VariableNames',{'k','y'}); ")
    assert names(base + "J = join(A, B, 'KeepKeys', true); v = J.Properties.VariableNames;") == ["k_A", "x", "k_B", "y"]
    assert num(base + "J = join(A, B, 'KeepKeys', true); v = [J.k_A J.k_B J.y];") == [[1, 1, 7], [2, 2, 8]]
    assert names(base + "J = join(A, B, 'KeepKeys', false); v = J.Properties.VariableNames;") == ["k", "x", "y"]
    diff = ("A = table([1;2],[10;20],'VariableNames',{'k','x'}); "
            "B = table([2;1],[8;7],'VariableNames',{'kk','y'}); ")
    assert names(diff + "J = join(A, B, 'LeftKeys','k','RightKeys','kk','KeepKeys',true); "
                 "v = J.Properties.VariableNames;") == ["k", "x", "kk", "y"]
    assert num(diff + "J = join(A, B, 'LeftKeys','k','RightKeys','kk','KeepKeys',true); v = [J.kk J.y];") == [
        [1, 7], [2, 8]]
    assert names(base + "J = join(A, B, 'KeepKeys', true, 'RightVariables', 'y'); v = J.Properties.VariableNames;") == [
        "k", "x", "y"]
    with pytest.raises(EvalError, match="unrecognized parameter name 'KeepKeys'"):
        run(base + "innerjoin(A, B, 'Keys', 'k', 'KeepKeys', true)")
    with pytest.raises(EvalError, match="must be 1 \\(true\\) or 0 \\(false\\)"):
        run(base + "join(A, B, 'KeepKeys', 'yes')")


def test_row_name_keys():
    base = ("A = table([10;30],'VariableNames',{'x'},'RowNames',{'c','a'}); "
            "B = table([1;2;3],'VariableNames',{'y'},'RowNames',{'b','a','c'}); ")
    assert num(base + "J = join(A, B, 'Keys','RowNames'); v = J.y';") == [[3, 2]]
    assert col_texts(base + "J = join(A, B, 'Keys','Row'); v = J.Properties.RowNames;") == ["c", "a"]
    assert num(base + "I = innerjoin(A, B, 'Keys','RowNames'); v = [I.x I.y];") == [[30, 2], [10, 3]]
    assert col_texts(base + "I = innerjoin(A, B, 'Keys','RowNames'); v = I.Properties.RowNames;") == ["a", "c"]
    assert col_texts(base + "O = outerjoin(A, B, 'Keys','RowNames','MergeKeys',true); v = O.Properties.RowNames;") == [
        "a", "b", "c"]
    got = num(base + "O = outerjoin(A, B, 'Keys','RowNames','MergeKeys',true); v = [O.x O.y];")
    assert got[0] == [30, 2]
    assert np.isnan(got[1][0]) and got[1][1] == 1
    assert got[2] == [10, 3]
    mixed = ("A = table([1;2],[10;20],'VariableNames',{'g','x'},'RowNames',{'b','a'}); "
             "B = table([2;1],[8;7],'VariableNames',{'g','y'},'RowNames',{'a','b'}); ")
    assert num(mixed + "J = join(A, B, 'Keys', {'Row','g'}); v = J.y';") == [[7, 8]]
    cross = ("A = table([10;20],'VariableNames',{'x'},'RowNames',{'a','b'}); "
             "B = table([\"b\";\"a\"],[8;7],'VariableNames',{'k','y'}); ")
    assert num(cross + "J = join(A, B, 'LeftKeys','Row','RightKeys','k'); v = J.y';") == [[7, 8]]
    assert num(cross + "I = innerjoin(A, B, 'LeftKeys','Row','RightKeys','k'); v = [I.x I.y];") == [[10, 7], [20, 8]]
    with pytest.raises(EvalError, match="no row names"):
        run("A = table([1;2],'VariableNames',{'k'}); B = table([1;2],'VariableNames',{'k'}); "
            "join(A, B, 'Keys','RowNames')")


def test_compatible_key_types_match():
    text = ("A = table({'b';'a'},[1;2],'VariableNames',{'k','x'}); "
            "B = table([\"a\";\"b\"],[8;9],'VariableNames',{'k','y'}); ")
    assert num(text + "I = innerjoin(A, B); v = [I.x I.y];") == [[2, 8], [1, 9]]
    mixed = ("A = table({'b';'a'},[1;2],'VariableNames',{'k','x'}); "
             "B = table([\"a\";\"c\"],[8;7],'VariableNames',{'k','y'}); ")
    assert col_texts(mixed + "O = outerjoin(A, B, 'MergeKeys', true); v = O.k;") == ["a", "b", "c"]
    got = num(mixed + "O = outerjoin(A, B, 'MergeKeys', true); v = [O.x O.y];")
    assert got[0] == [2, 8]
    assert got[1][0] == 1 and np.isnan(got[1][1])
    assert np.isnan(got[2][0]) and got[2][1] == 7
    nums = ("A = table([1;2],[10;20],'VariableNames',{'k','x'}); "
            "B = table(int8([2;1;3]),[8;7;6],'VariableNames',{'k','y'}); ")
    assert num(nums + "J = join(A, B(1:2,:), 'Keys','k'); v = J.y';") == [[7, 8]]
    assert num(nums + "I = innerjoin(A, B); v = I.y';") == [[7, 8]]
    assert num(nums + "O = outerjoin(A, B, 'MergeKeys', true); v = [O.k O.y];") == [[1, 7], [2, 8], [3, 6]]


def test_expression_inputs_use_left_and_right_suffixes():
    base = ("A = table([1;2],[3;4],'VariableNames',{'k','x'}); "
            "B = table([2;1],[5;6],'VariableNames',{'k','x'}); ")
    assert names(base + "J = join(A(1:2,:), B, 'Keys','k'); v = J.Properties.VariableNames;") == ["k", "x_left", "x_B"]
    assert names(base + "J = join(A, B(:,1:2), 'Keys','k'); v = J.Properties.VariableNames;") == ["k", "x_A", "x_right"]
    assert names(base + "J = innerjoin(table(A.k, A.x, 'VariableNames', {'k','x'}), B, 'Keys','k'); "
                 "v = J.Properties.VariableNames;") == ["k", "x_left", "x_B"]
    assert names(base + "J = join(A, A, 'Keys','k'); v = J.Properties.VariableNames;") == ["k", "x_A_1", "x_A"]
    assert num(base + "J = join(A, A, 'Keys','k'); v = [J.x_A_1 J.x_A];") == [[3, 3], [4, 4]]
    wider = ("A = table([1;2],[3;4],'VariableNames',{'k','x'}); "
             "B = table([1;2;4],[5;6;7],'VariableNames',{'k','x'}); ")
    assert names(wider + "O = outerjoin(A(1:2,:), B, 'Keys','k'); v = O.Properties.VariableNames;") == [
        "k_left", "x_left", "k_B", "x_B"]


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
    "groupsummary([1;2], [1], 'sum')",
    "groupcounts(table([1;2]), 'nope')",
])
def test_errors_are_matlab_errors(code):
    with pytest.raises(EvalError):
        run(code)
