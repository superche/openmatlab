"""findgroups IncludeMissing, splitapply table output, groupcounts, grouptransform, groupfilter.

Issues #1054 and #1055. Numbers below are the public MathWorks examples, or the
same formulas those pages name (sample standard deviation, 2-norm, [0, 1] rescale).
"""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

_HEALTH = (
    "HealthStatus = categorical({'Poor';'Good';'Fair';'Fair';'Poor';'Excellent';'Good';'Excellent'});"
    "Smoker = [true;false;false;true;true;false;false;true];"
)
_PROFIT = (
    "timeStamps = datetime([2017 3 4; 2017 3 2; 2017 3 15; 2017 3 10; 2017 3 14; 2017 3 31;"
    " 2017 3 25; 2017 3 29; 2017 3 21; 2017 3 18]);"
    "profit = [2032;3071;1185;2587;1998;2899;3112;909;2619;3085];"
)
# Published grouptransform "norm" example, day-name bins, input order.
_NORM = [0.42069, 1.0, 0.79344, 0.66582, 0.60654, 0.74612, 0.64428, 0.60864, 0.79506, 0.63869]


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


def test_include_missing_numbers_the_nan_group_and_keeps_it_in_id():
    assert_rows(
        "[G, ID] = findgroups([1;NaN;2], 'IncludeMissing', true); v = [G' ID'];",
        [[1, 3, 2, 1, 2, np.nan]],
    )
    assert_rows(
        "[G, ID] = findgroups([1;NaN;NaN], 'IncludeMissing', false); v = [isnan(G') ID'];",
        [[0, 1, 1, 1]],
    )
    # No missing values: the flag does not renumber.
    assert_rows(
        "v = findgroups([3;1;3], 'IncludeMissing', true)';",
        [[2, 1, 2]],
    )
    # A missing second key sorts last inside that first-key, not after every later key.
    assert_rows(
        "[G, a, b] = findgroups([1;1;2], [10;NaN;20], 'IncludeMissing', true); v = [G' a' b'];",
        [[1, 2, 3, 1, 1, 2, 10, np.nan, 20]],
    )


def test_include_missing_on_a_table_puts_the_nan_row_in_tid():
    s = run("T = table([1;NaN;1], {'a';'b';'a'}); [G, TID] = findgroups(T, 'IncludeMissing', true);")
    assert np.allclose(np.asarray(s.workspace.get("G").backend_buffer(), float).reshape(-1), [1, 2, 1])
    assert np.allclose(np.asarray(s.workspace.get("TID").cols[0].backend_buffer(), float).reshape(-1),
                       [1, np.nan], equal_nan=True)
    assert [row[0].text for row in s.workspace.get("TID").cols[1].rows] == ["a", "b"]
    omitted = run("T = table([1;NaN;1]); [G, TID] = findgroups(T);")
    assert omitted.workspace.get("TID").nrows == 1
    assert np.isnan(np.asarray(omitted.workspace.get("G").backend_buffer(), float).reshape(-1)[1])


def test_include_missing_rejects_a_non_logical_flag():
    with pytest.raises(EvalError, match="IncludeMissing' must be 1"):
        run("findgroups([1;NaN], 'IncludeMissing', 'yes')")
    with pytest.raises(EvalError, match="not enough input arguments"):
        run("findgroups('IncludeMissing', true)")


def test_splitapply_stacks_table_outputs_in_group_order():
    code = (
        "G = findgroups([1;1;2;2]);"
        "S = splitapply(@(x) table(sum(x), numel(x), 'VariableNames', {'total','n'}), [10;20;30;40], G);"
        "v = [S.total S.n];"
    )
    assert_rows(code, [[30, 2], [70, 2]])
    stacked = (
        "S = splitapply(@(x) table(x, 'VariableNames', {'x'}), [10;30;20;40], [1;2;1;2]); v = S.x';"
    )
    assert_rows(stacked, [[10, 20, 30, 40]])
    with pytest.raises(EvalError, match="same variable names"):
        run("splitapply(@(x) table(x, 'VariableNames', {char('a' + (x(1)==10))}), [10;20;30], [1;1;2])")
    with pytest.raises(EvalError, match="one row per group"):
        run("splitapply(@(x) x, [1;2;3], [1;1;2])")


def test_groupcounts_include_empty_matches_the_published_table():
    code = (
        _HEALTH
        + "T = table(HealthStatus, Smoker);"
        + "C = groupcounts(T, {'HealthStatus','Smoker'}, 'IncludeEmptyGroups', true);"
    )
    s = run(code)
    C = s.workspace.get("C")
    assert C.names == ["HealthStatus", "Smoker", "GroupCount", "Percent"]
    assert C.cols[0].labels() == ["Excellent", "Excellent", "Fair", "Fair", "Good", "Good", "Poor", "Poor"]
    assert np.asarray(C.cols[1].backend_buffer()).reshape(-1).tolist() == [False, True] * 4
    assert_rows(code + "v = [C.GroupCount C.Percent];", [
        [1, 12.5], [1, 12.5], [1, 12.5], [1, 12.5], [2, 25], [0, 0], [0, 0], [2, 25],
    ])
    # The flag off still drops the two empty combinations. Counts stay 1,1,1,1,2,2.
    assert_rows(
        _HEALTH + "T = table(HealthStatus, Smoker); C = groupcounts(T, {'HealthStatus','Smoker'});"
        "v = C.GroupCount';",
        [[1, 1, 1, 1, 2, 2]],
    )
    # A plain numeric key has no empty level. The old error probe for this call is the success path now.
    assert_rows(
        "T = table([1;1;2],[4;5;6]); C = groupcounts(T, 'Var1', 'IncludeEmptyGroups', true);"
        "v = [C.GroupCount C.Percent];",
        [[2, 200 / 3], [1, 100 / 3]],
    )


def test_groupcounts_on_a_vector_returns_sorted_counts():
    # Public example: [1 1 2 2 3 5 3 3 1 4]'.
    assert_rows(
        "[B,BG,BP] = groupcounts([1;1;2;2;3;5;3;3;1;4]); v = [B BG BP];",
        [[3, 1, 30], [2, 2, 20], [3, 3, 30], [1, 4, 10], [1, 5, 10]],
    )
    # A plain numeric vector has no empty groups to invent.
    assert_rows(
        "[B,BG] = groupcounts([1;3;1], 'IncludeEmptyGroups', true); v = [BG B];",
        [[1, 2], [3, 1]],
    )
    assert_rows(
        "[B,BG,BP] = groupcounts([true;true], 'IncludeEmptyGroups', true); v = [double(BG) B BP];",
        [[0, 0, 0], [1, 2, 100]],
    )
    assert_rows(
        "[B,BG] = groupcounts([1;NaN;1], 'IncludeMissingGroups', false); v = [BG B];",
        [[1, 2]],
    )
    assert_rows(
        "[B,BG] = groupcounts([1;NaN;1]); v = [BG B];",
        [[1, 2], [np.nan, 1]],
    )


def test_groupcounts_on_several_vectors_and_bin_edges():
    s = run(
        _HEALTH + "[B,BG,BP] = groupcounts({HealthStatus, Smoker}, 'IncludeEmptyGroups', true);"
    )
    assert np.allclose(np.asarray(s.workspace.get("B").backend_buffer(), float).reshape(-1),
                       [1, 1, 1, 1, 2, 0, 0, 2])
    bg = s.workspace.get("BG")
    assert bg.rows[0][0].labels() == ["Excellent", "Excellent", "Fair", "Fair", "Good", "Good", "Poor", "Poor"]
    assert np.asarray(bg.rows[0][1].backend_buffer()).reshape(-1).tolist() == [False, True] * 4
    items = (
        "ItemsSold = [14;13;8;5;10;16;8;6;7;11];"
        "T = table(ItemsSold);"
        "C = groupcounts(T, 'ItemsSold', [0 4 8 12 16]);"
    )
    got = run(items)
    assert got.workspace.get("C").names == ["disc_ItemsSold", "GroupCount", "Percent"]
    assert got.workspace.get("C").cols[0].labels() == ["[4, 8)", "[8, 12)", "[12, 16]"]
    assert_rows(items + "v = [C.GroupCount C.Percent];", [[3, 30], [4, 40], [3, 30]])
    # A matrix is grouped by its rows. BG is one column vector per input column.
    matrix = run("[B,BG] = groupcounts([1 10; 1 10; 1 20]);")
    assert np.asarray(matrix.workspace.get("B").backend_buffer(), float).reshape(-1).tolist() == [2, 1]
    bgm = matrix.workspace.get("BG")
    assert np.asarray(bgm.rows[0][0].backend_buffer(), float).reshape(-1).tolist() == [1, 1]
    assert np.asarray(bgm.rows[0][1].backend_buffer(), float).reshape(-1).tolist() == [10, 20]
    # Published day-name counts. Empty Sunday and Monday appear only with the flag.
    days = (
        "t = datetime([2017 3 4; 2017 3 2; 2017 3 15; 2017 3 10; 2017 3 14; 2017 3 31;"
        " 2017 3 25; 2017 3 29; 2017 3 21; 2017 3 18]); T = table(t);"
    )
    named = run(days + "C = groupcounts(T, 't', 'dayname');")
    assert named.workspace.get("C").cols[0].labels() == ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    assert_rows(days + "C = groupcounts(T, 't', 'dayname'); v = [C.GroupCount C.Percent];", [
        [2, 20], [2, 20], [1, 10], [2, 20], [3, 30],
    ])
    full = run(days + "C = groupcounts(T, 't', 'dayname', 'IncludeEmptyGroups', true);")
    assert full.workspace.get("C").cols[0].labels() == [
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    ]
    assert_rows(
        days + "C = groupcounts(T, 't', 'dayname', 'IncludeEmptyGroups', true); v = C.GroupCount';",
        [[0, 0, 2, 2, 1, 2, 3]],
    )
    with pytest.raises(EvalError, match="IncludeEmptyGroups' must be 1"):
        run("groupcounts([1;2], 'IncludeEmptyGroups', 'yes')")


def test_grouptransform_norm_and_fills_match_the_published_examples():
    code = _PROFIT + "T = table(timeStamps, profit); G = grouptransform(T, 'timeStamps', 'dayname', 'norm');"
    s = run(code)
    assert s.workspace.get("G").names == ["timeStamps", "profit", "dayname_timeStamps"]
    assert_rows(code + "v = G.profit';", [_NORM])
    assert s.workspace.get("G").cols[2].labels() == [
        "Saturday", "Thursday", "Wednesday", "Friday", "Tuesday",
        "Friday", "Saturday", "Wednesday", "Tuesday", "Saturday",
    ]
    filled = (
        "team = [1;2;3;1;2;3;1;2;3];"
        "pct = [14.2;28.1;11.5;NaN;NaN;19.3;46.1;51.2;30.3];"
        "T = table(team, pct);"
        "G = grouptransform(T, 'team', 'linearfill', 'pct'); v = G.pct';"
    )
    assert_rows(filled, [[14.2, 28.1, 11.5, 30.15, 39.65, 19.3, 46.1, 51.2, 30.3]])
    appended = run(
        "team = [1;2;3;1;2;3;1;2;3]; pct = [14.2;28.1;11.5;NaN;NaN;19.3;46.1;51.2;30.3];"
        "T = table(team, pct);"
        "G = grouptransform(T, 'team', 'linearfill', 'pct', 'ReplaceValues', false);"
    )
    assert appended.workspace.get("G").names == ["team", "pct", "linearfill_pct"]
    assert np.isnan(np.asarray(appended.workspace.get("G").cols[1].backend_buffer(), float).reshape(-1)[3])


def test_grouptransform_scales_and_function_handles():
    assert_rows(
        "v = grouptransform([10;20;30], [1;1;1], 'zscore')';",
        [[-1, 0, 1]],
    )
    assert_rows(
        "v = grouptransform([10;30], [1;1], 'meancenter')';",
        [[-10, 10]],
    )
    assert_rows(
        "v = grouptransform([10;30], [1;1], 'rescale')';",
        [[0, 1]],
    )
    assert_rows("v = grouptransform([-5], [1], 'norm');", [[-1]])
    # A missing grouping key is its own group, so the other rows are not centered with it.
    assert_rows(
        "v = grouptransform([10;20;30], [1;NaN;1], 'meancenter')';",
        [[-10, 0, 10]],
    )
    assert_rows(
        "v = grouptransform([1;NaN;5;NaN], [1;1;2;2], 'meanfill')';",
        [[1, 1, 5, 5]],
    )
    # A leading missing value is not extrapolated.
    assert_rows(
        "v = grouptransform([NaN;0;4], [1;1;1], 'linearfill')';",
        [[np.nan, 0, 4]],
    )
    assert_rows(
        "v = grouptransform([10;20;30], [1;1;1], @(x) mean(x))';",
        [[20, 20, 20]],
    )
    assert_rows(
        "[B,BG] = grouptransform([10;20;30;40], [1;1;2;2], 'meancenter'); v = [B BG];",
        [[-5, 1], [5, 1], [-5, 2], [5, 2]],
    )
    # Constant group: sample standard deviation is 0, so the z-score is missing.
    assert_rows(
        "v = grouptransform([4;4], [1;1], 'zscore')';",
        [[np.nan, np.nan]],
    )
    with pytest.raises(EvalError, match="method must be"):
        run("grouptransform([1;2], [1;1], 'banana')")
    with pytest.raises(EvalError, match="IncludedEdge"):
        run("grouptransform(table([1;2],[3;4],'VariableNames',{'g','x'}), 'g', 'zscore', 'IncludedEdge', 'right')")
    with pytest.raises(EvalError, match="one row"):
        run("grouptransform([1;2;3], [1;1;1], @(x) [1;2])")


def test_groupfilter_keeps_rows_in_input_order():
    base = "groupID = [1;1;1;2;2;3]; sample = [3;1;2;9;8;5]; T = table(groupID, sample);"
    assert_rows(
        base + "G = groupfilter(T, 'groupID', @(x) numel(x) > 2); v = G.sample';",
        [[3, 1, 2]],
    )
    assert_rows(
        base + "G = groupfilter(T, 'groupID', @(x) min(x) > 0 & max(x) < 6); v = [G.groupID G.sample];",
        [[1, 3], [1, 1], [1, 2], [3, 5]],
    )
    assert_rows(
        "day = [1;1;1;1;2;2;2;2]; temp = [67;65;71;55;61;79;58;78]; T = table(day, temp);"
        "G = groupfilter(T, 'day', @(x) x == max(x)); v = G.temp';",
        [[71, 79]],
    )
    # Published day-name filter: one maximum per day, in the order those rows occur.
    assert_rows(
        _PROFIT + "[B,BG] = groupfilter(profit, timeStamps, 'dayname', @(x) x == max(x)); v = B';",
        [[3071, 1185, 2899, 3112, 2619]],
    )
    labels = run(
        _PROFIT + "[B,BG] = groupfilter(profit, timeStamps, 'dayname', @(x) x == max(x));"
    ).workspace.get("BG").labels()
    assert labels == ["Thursday", "Wednesday", "Friday", "Saturday", "Tuesday"]


def test_groupfilter_ands_data_variables_and_rejects_a_bad_mask():
    code = (
        "T = table([1;1;2], [1;2;3], [1;-1;4], 'VariableNames', {'g','x','y'});"
        "G = groupfilter(T, 'g', @(v) all(v > 0)); v = [G.g G.x G.y];"
    )
    assert_rows(code, [[2, 3, 4]])
    assert_rows(
        "T = table([1;1;2], [1;2;3], [1;-1;4], 'VariableNames', {'g','x','y'});"
        "G = groupfilter(T, 'g', @(v) all(v > 0), 'x'); v = G.x';",
        [[1, 2, 3]],
    )
    height = (
        "groupID = [1;2;3;1;2;3;1;2;3]; Height = [62;61;59;66;70;72;57;67;71];"
        "T = table(groupID, Height);"
        "G = groupfilter(T, 'groupID', @(x) min(x) >= 60, 'Height'); v = G.Height';"
    )
    assert_rows(height, [[61, 70, 67]])
    with pytest.raises(EvalError, match="function handle"):
        run("groupfilter([1;2], [1;1], 'numel')")
    with pytest.raises(EvalError, match="logical"):
        run("groupfilter([1;2;3], [1;1;2], @(x) sum(x))")
    with pytest.raises(EvalError, match="one element per group row"):
        run("groupfilter([1;2;3], [1;1;1], @(x) [true;false])")
