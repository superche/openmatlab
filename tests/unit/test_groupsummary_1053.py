"""groupsummary bins, array input, naming, and multi-output methods (#1053)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def rows(code, name="v"):
    return np.asarray(run(code).workspace.get(name).backend_buffer(), float)


def assert_rows(code, expected, name="v"):
    got = rows(code, name)
    exp = np.asarray(expected, float)
    assert got.shape == exp.shape, (got.tolist(), exp.tolist())
    assert np.allclose(got, exp, equal_nan=True)


# Public groupsummary example: bin ItemsSold, then mean and mode of Profit.
_ITEMS = (
    "ItemsSold = [14;13;8;5;10;16;8;6;7;11];"
    "Profit = [2032;3071;1185;2587;1998;2899;3112;909;2619;3085];"
    "T = table(ItemsSold, Profit);"
)


def test_doc_bin_edges_mean_and_mode():
    s = run(_ITEMS + "S = groupsummary(T, 'ItemsSold', [0 4 8 12 16], {'mean','mode'}, 'Profit');")
    S = s.workspace.get("S")
    assert S.names == ["disc_ItemsSold", "GroupCount", "mean_Profit", "mode_Profit"]
    assert S.cols[0].labels() == ["[4, 8)", "[8, 12)", "[12, 16]"]
    assert_rows(
        _ITEMS + "S = groupsummary(T, 'ItemsSold', [0 4 8 12 16], {'mean','mode'}, 'Profit');"
        "v = [S.GroupCount S.mean_Profit S.mode_Profit];",
        [[3, 2038.333333333333, 909], [4, 2345, 1185], [3, 2667.333333333333, 2032]],
    )


def test_included_edge_moves_the_shared_endpoint():
    code = "x = [1;2;3;4]; T = table(x, x, 'VariableNames', {'g','x'});"
    left = run(code + "S = groupsummary(T, 'g', [1 2 4], 'sum', 'x', 'IncludedEdge', 'left');")
    right = run(code + "S = groupsummary(T, 'g', [1 2 4], 'sum', 'x', 'IncludedEdge', 'right');")
    assert left.workspace.get("S").cols[0].labels() == ["[1, 2)", "[2, 4]"]
    assert right.workspace.get("S").cols[0].labels() == ["[1, 2]", "(2, 4]"]
    assert_rows(code + "S = groupsummary(T, 'g', [1 2 4], 'sum', 'x'); v = [S.GroupCount S.sum_x];", [[1, 1], [3, 9]])
    assert_rows(
        code + "S = groupsummary(T, 'g', [1 2 4], 'sum', 'x', 'IncludedEdge', 'right'); v = [S.GroupCount S.sum_x];",
        [[2, 3], [2, 7]],
    )


def test_equal_width_bin_count_and_empty_bins():
    code = (
        "T = table([1;2;3;4], [10;20;30;40], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', 2, 'sum', 'x', 'IncludeEmptyGroups', true);"
    )
    s = run(code)
    assert s.workspace.get("S").cols[0].labels() == ["[1, 2.5)", "[2.5, 4]"]
    assert_rows(code + "v = [S.GroupCount S.sum_x];", [[2, 30], [2, 70]])
    empty = (
        "T = table([0.5;0.5], [1;3], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', [0 1 2 3], {'sum','mean'}, 'x', 'IncludeEmptyGroups', true);"
    )
    assert run(empty).workspace.get("S").cols[0].labels() == ["[0, 1)", "[1, 2)", "[2, 3]"]
    assert_rows(empty + "v = [S.GroupCount S.sum_x S.mean_x];", [[2, 4, 2], [0, 0, np.nan], [0, 0, np.nan]])


def test_values_outside_the_edges_are_a_missing_group():
    code = "T = table([1;5;100], [10;20;30], 'VariableNames', {'g','x'});"
    kept = run(code + "S = groupsummary(T, 'g', [0 10], 'sum', 'x');")
    assert kept.workspace.get("S").cols[0].labels() == ["[0, 10]", "<undefined>"]
    assert_rows(code + "S = groupsummary(T, 'g', [0 10], 'sum', 'x'); v = [S.GroupCount S.sum_x];", [[2, 30], [1, 30]])
    assert_rows(
        code + "S = groupsummary(T, 'g', [0 10], 'sum', 'x', 'IncludeMissingGroups', false); v = S.sum_x;",
        [[30]],
    )


def test_dayname_matches_the_published_week():
    # Tuesday 2308.5 (n=2), Wednesday 1047, Thursday 3071, Friday 2743 (n=2), Saturday 2743 (n=3).
    code = (
        "Timestamps = datetime([2017 3 4; 2017 3 2; 2017 3 15; 2017 3 10; 2017 3 14; 2017 3 31;"
        " 2017 3 25; 2017 3 29; 2017 3 21; 2017 3 18]);"
        "Profit = [2032;3071;1185;2587;1998;2899;3112;909;2619;3085];"
        "T = table(Timestamps, Profit);"
        "S = groupsummary(T, 'Timestamps', 'dayname', 'mean', 'Profit', 'VariableNamingRule', 'noprefix');"
    )
    s = run(code)
    S = s.workspace.get("S")
    assert S.names == ["dayname_Timestamps", "GroupCount", "Profit"]
    assert S.cols[0].labels() == ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    assert_rows(code + "v = [S.GroupCount S.Profit];", [[2, 2308.5], [2, 1047], [1, 3071], [2, 2743], [3, 2743]])
    full = (
        "T = table(datetime([2017 3 4; 2017 3 14]), [1;3], 'VariableNames', {'t','x'});"
        "S = groupsummary(T, 't', 'dayname', 'sum', 'x', 'IncludeEmptyGroups', true);"
    )
    assert run(full).workspace.get("S").cols[0].labels() == [
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    ]


def test_array_input_returns_summary_groups_and_counts():
    code = "[B,BG,BC] = groupsummary([10;20;30;40], [1;1;2;2], {'sum','mean'}); v = [B BG BC];"
    assert_rows(code, [[30, 15, 1, 2], [70, 35, 2, 2]])
    # One data column, then the next: mean and sum of column 1, then of column 2.
    assert_rows(
        "B = groupsummary([1 10; 2 20; 3 30; 4 40], [1;1;2;2], {'mean','sum'}); v = B;",
        [[1.5, 3, 15, 30], [3.5, 7, 35, 70]],
    )
    # Each column of a grouping matrix is its own vector. Empty combinations are real groups.
    wide = "[B,BG,BC] = groupsummary([5;6], [1 2; 3 4], 'sum', 'IncludeEmptyGroups', true); v = [B BC];"
    assert_rows(wide, [[5, 1], [0, 0], [0, 0], [6, 1]])
    # The published categorical-by-logical example, on vectors rather than a table.
    doc = (
        "HealthStatus = categorical({'Poor';'Good';'Fair';'Fair';'Poor';'Excellent';'Good';'Excellent'});"
        "Smoker = [true;false;false;true;true;false;false;true];"
        "Weight = [176;153;131;133;119;120;140;129];"
        "[B,BG,BC] = groupsummary(Weight, {HealthStatus, Smoker}, 'mean', 'IncludeEmptyGroups', true);"
    )
    s = run(doc)
    assert s.workspace.get("BG").shape == (1, 2)
    assert s.workspace.get("BG").get(0, 0).labels() == ["Excellent", "Excellent", "Fair", "Fair", "Good", "Good", "Poor", "Poor"]
    assert np.asarray(s.workspace.get("BG").get(0, 1).backend_buffer()).reshape(-1).tolist() == [False, True] * 4
    assert_rows(doc + "v = [B BC];", [[120, 1], [129, 1], [131, 1], [133, 1], [146.5, 2], [np.nan, 0], [np.nan, 0], [147.5, 2]])


def test_variable_naming_rule():
    base = "T = table([1;1;2;2], [10;20;30;40], 'VariableNames', {'g','x'});"
    numbered = run(base + "S = groupsummary(T, 'g', {'min', @(x) max(x)}, 'x');")
    assert numbered.workspace.get("S").names == ["g", "GroupCount", "min_x", "fun1_x"]
    named = run(base + "f = @(x) max(x) - min(x); S = groupsummary(T, 'g', f, 'x', 'VariableNamingRule', 'methodname');")
    assert named.workspace.get("S").names[2] == "@(x)max(x)-min(x)_x"
    plain = run(base + "S = groupsummary(T, 'g', 'mean', 'x', 'VariableNamingRule', 'noprefix');")
    assert plain.workspace.get("S").names == ["g", "GroupCount", "x"]
    assert_rows(base + "S = groupsummary(T, 'g', 'mean', 'x', 'VariableNamingRule', 'noprefix'); v = S.x;", [[15], [35]])


def test_function_row_and_multiple_outputs(tmp_path):
    code = (
        "T = table([1;1;2;2], [10;20;30;40], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', @(x) [min(x) max(x)], 'x');"
    )
    assert run(code).workspace.get("S").names == ["g", "GroupCount", "fun1_x"]
    assert_rows(code + "v = S.fun1_x;", [[10, 20], [30, 40]])
    (tmp_path / "span1053.m").write_text("function [lo, hi] = span1053(x)\nlo = min(x);\nhi = max(x);\nend\n")
    paired = (
        f"addpath('{tmp_path}');"
        "T = table([1;1;2;2], [10;20;30;40], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', @span1053, 'x'); v = S.fun1_x;"
    )
    assert_rows(paired, [[10, 20], [30, 40]])
    both = (
        "T = table([1;1;2;2], [10;20;30;40], [3;5;7;9], 'VariableNames', {'g','x','y'});"
        "S = groupsummary(T, 'g', @(x,y) sum(x.*y), {'x','y'});"
    )
    assert run(both).workspace.get("S").names == ["g", "GroupCount", "fun1_x_y"]
    assert_rows(both + "v = S.fun1_x_y;", [[130], [570]])


def test_multicolumn_group_keeps_observed_rows_only():
    code = (
        "T = table([1 2; 3 4], [5;6], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', 'sum', 'IncludeEmptyGroups', true);"
    )
    s = run(code)
    assert np.asarray(s.workspace.get("S").cols[0].backend_buffer()).tolist() == [[1.0, 2.0], [3.0, 4.0]]
    assert_rows(code + "v = [S.GroupCount S.sum_x];", [[1, 5], [1, 6]])


@pytest.mark.parametrize("code", [
    "groupsummary(table([1;2],[3;4]), 'Var1', 'mean', 'Var2', 'IncludedEdge', 'right')",
    "groupsummary(table([1;2],[3;4]), 'Var1', 'mean', 'Var2', 'VariableNamingRule', 'fancy')",
    "groupsummary(table([1;2],[3;4]), 'Var1', {'min','max'}, 'Var2', 'VariableNamingRule', 'noprefix')",
    "groupsummary([1;2;3], [1;1;2], 'mean', 'VariableNamingRule', 'noprefix')",
    "groupsummary([1;2], [1], 'sum')",
    "T = table([1;1;2],[3;4;5],[6;7;8],'VariableNames',{'a','b','x'}); groupsummary(T, {'a','b'}, {[0 1],[0 1 2],[0 10]}, 'sum', 'x')",
])
def test_remaining_gaps_are_eval_errors(code):
    with pytest.raises(EvalError):
        run(code)
