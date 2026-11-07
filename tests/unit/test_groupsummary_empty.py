"""groupsummary IncludeEmptyGroups, story methods, and missing groups (M17 #742)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

_DOC = (
    "HealthStatus = categorical({'Poor';'Good';'Fair';'Fair';'Poor';'Excellent';'Good';'Excellent'});"
    "Smoker = [true;false;false;true;true;false;false;true];"
    "Weight = [176;153;131;133;119;120;140;129];"
    "T = table(HealthStatus, Smoker, Weight);"
)


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


def test_doc_example_include_empty_groups():
    # Public groupsummary example: categorical x logical, two combinations absent.
    s = run(_DOC + "S = groupsummary(T, {'HealthStatus','Smoker'}, 'mean', 'Weight', 'IncludeEmptyGroups', true);")
    S = s.workspace.get("S")
    assert S.names == ["HealthStatus", "Smoker", "GroupCount", "mean_Weight"]
    assert S.cols[0].labels() == ["Excellent", "Excellent", "Fair", "Fair", "Good", "Good", "Poor", "Poor"]
    assert np.asarray(S.cols[1].backend_buffer()).reshape(-1).tolist() == [False, True] * 4
    assert_rows(
        _DOC + "S = groupsummary(T, {'HealthStatus','Smoker'}, 'mean', 'Weight', 'IncludeEmptyGroups', true);"
        "v = [S.GroupCount S.mean_Weight];",
        [[1, 120], [1, 129], [1, 131], [1, 133], [2, 146.5], [0, np.nan], [0, np.nan], [2, 147.5]],
    )


def test_doc_example_omits_empty_groups_by_default():
    s = run(_DOC + "S = groupsummary(T, {'HealthStatus','Smoker'}, 'mean', 'Weight');")
    S = s.workspace.get("S")
    assert S.cols[0].labels() == ["Excellent", "Excellent", "Fair", "Fair", "Good", "Poor"]
    assert np.asarray(S.cols[1].backend_buffer()).reshape(-1).tolist() == [False, True, False, True, False, True]
    assert_rows(
        _DOC + "S = groupsummary(T, {'HealthStatus','Smoker'}, 'mean', 'Weight'); v = [S.GroupCount S.mean_Weight];",
        [[1, 120], [1, 129], [1, 131], [1, 133], [2, 146.5], [2, 147.5]],
    )


def test_unused_category_follows_category_order_not_alphabetical():
    code = (
        "T = table(categorical({'b';'a'}, {'b','a','c'}), [2;4], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', {'mean','sum','min','max','std'}, 'x', 'IncludeEmptyGroups', true);"
    )
    s = run(code)
    S = s.workspace.get("S")
    assert S.cols[0].labels() == ["b", "a", "c"]
    assert S.names == ["g", "GroupCount", "mean_x", "sum_x", "min_x", "max_x", "std_x"]
    assert_rows(
        code + "v = [S.GroupCount S.mean_x S.sum_x S.min_x S.max_x S.std_x];",
        [
            [1, 2, 2, 2, 2, 0],
            [1, 4, 4, 4, 4, 0],
            [0, np.nan, 0, np.nan, np.nan, np.nan],
        ],
    )


def test_story_methods_skip_nan_data_and_groupcount_keeps_the_row():
    code = (
        "T = table([1;1;1], [2;NaN;4], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', {'mean','sum','min','max','std'}, 'x');"
        "v = [S.GroupCount S.mean_x S.sum_x S.min_x S.max_x S.std_x];"
    )
    assert_rows(code, [[3, 3, 6, 2, 4, math.sqrt(2)]])


def test_all_nan_data_group_sums_to_zero():
    code = (
        "T = table([1;1], [NaN;NaN], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', {'mean','sum','min','max','std'}, 'x');"
        "v = [S.GroupCount S.mean_x S.sum_x S.min_x S.max_x S.std_x];"
    )
    assert_rows(code, [[2, np.nan, 0, np.nan, np.nan, np.nan]])


def test_missing_group_is_last_unless_excluded():
    base = "T = table([1;NaN;1], [4;5;6], 'VariableNames', {'g','x'});"
    assert_rows(base + "S = groupsummary(T, 'g', 'sum', 'x'); v = [S.g S.sum_x S.GroupCount];", [[1, 10, 2], [np.nan, 5, 1]])
    assert_rows(
        base + "S = groupsummary(T, 'g', 'sum', 'x', 'IncludeMissingGroups', false); v = [S.g S.sum_x S.GroupCount];",
        [[1, 10, 2]],
    )


def _text_keys(col):
    """Cellstr or string grouping column, top to bottom. ``None`` is ``<missing>``."""
    from openmatlab.runtime import string_array as sa
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(col, CellValue):
        return [col.rows[i][0].text for i in range(col.shape[0])]
    if getattr(col, "is_string", False):
        return [None if x is None else str(x) for x in sa.to_grid(col).reshape(-1)]
    raise AssertionError(type(col).__name__)


def _summary(code, name="S"):
    s = run(code)
    return s.workspace.get(name)


def test_cellstr_empty_is_a_missing_group_key():
    # '' in a cellstr is the standard missing value. It is its own group, last,
    # unless IncludeMissingGroups is false. A space is a real key.
    kept = _summary("T = table({'b';'';'a';'';' '}, [1;2;3;4;5]); S = groupsummary(T, 'Var1', 'sum');")
    assert _text_keys(kept.cols[0]) == [" ", "a", "b", ""]
    assert_rows(
        "T = table({'b';'';'a';'';' '}, [1;2;3;4;5]); S = groupsummary(T, 'Var1', 'sum'); v = [S.sum_Var2 S.GroupCount];",
        [[5, 1], [3, 1], [1, 1], [6, 2]],
    )
    dropped = _summary(
        "T = table({'a';'b';''}, [1;2;3]); S = groupsummary(T, 'Var1', 'sum', 'IncludeMissingGroups', false);"
    )
    assert _text_keys(dropped.cols[0]) == ["a", "b"]
    assert_rows(
        "T = table({'a';'b';''}, [1;2;3]); S = groupsummary(T, 'Var1', 'sum', 'IncludeMissingGroups', false);"
        "v = [S.sum_Var2 S.GroupCount];",
        [[1, 1], [2, 1]],
    )
    only = _summary("T = table({'';''}, [1;2]); S = groupsummary(T, 'Var1', 'sum', 'IncludeMissingGroups', false);")
    assert only.nrows == 0
    # Same ranks when IncludeEmptyGroups is on: '' is not an invented level, and it stays last.
    both = _summary(
        "T = table({'a';'';'a'}, [1;2;3], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', 'sum', 'x', 'IncludeEmptyGroups', true);"
    )
    assert _text_keys(both.cols[0]) == ["a", ""]
    assert_rows(
        "T = table({'a';'';'a'}, [1;2;3], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', 'sum', 'x', 'IncludeEmptyGroups', true, 'IncludeMissingGroups', false);"
        "v = [S.sum_x S.GroupCount];",
        [[4, 2]],
    )
    # groupcounts uses the same ranks.
    counted = _summary("T = table({'a';'b';''}, [1;2;3]); C = groupcounts(T, 'Var1');", name="C")
    assert _text_keys(counted.cols[0]) == ["a", "b", ""]
    dropped_counts = _summary(
        "T = table({'a';'b';''}, [1;2;3]); C = groupcounts(T, 'Var1', 'IncludeMissingGroups', false);",
        name="C",
    )
    assert _text_keys(dropped_counts.cols[0]) == ["a", "b"]


def test_string_missing_group_key_follows_ismissing():
    # <missing> is a missing group key. "" is not, and it sorts first.
    kept = _summary('T = table(["b"; missing; "a"; ""], [1;2;3;4]); S = groupsummary(T, "Var1", "sum");')
    assert _text_keys(kept.cols[0]) == ["", "a", "b", None]
    assert_rows(
        'T = table(["b"; missing; "a"; ""], [1;2;3;4]); S = groupsummary(T, "Var1", "sum");'
        "v = [S.sum_Var2 S.GroupCount];",
        [[4, 1], [3, 1], [1, 1], [2, 1]],
    )
    dropped = _summary(
        'T = table(["a"; missing; ""], [1;2;3]);'
        'S = groupsummary(T, "Var1", "sum", "IncludeMissingGroups", false);'
    )
    assert _text_keys(dropped.cols[0]) == ["", "a"]
    assert_rows(
        'T = table(["a"; missing; ""], [1;2;3]);'
        'S = groupsummary(T, "Var1", "sum", "IncludeMissingGroups", false);'
        "v = [S.sum_Var2 S.GroupCount];",
        [[3, 1], [1, 1]],
    )


def test_cellstr_missing_sorts_last_inside_its_column():
    # Column 1 missing stays after every 'a' row, including an 'a' whose other key is NaN.
    code = (
        "T = table({'a';'';'a'}, [1;1;NaN], [10;20;30], 'VariableNames', {'g','n','x'});"
        "S = groupsummary(T, {'g','n'}, 'sum', 'x');"
    )
    s = _summary(code)
    assert _text_keys(s.cols[0]) == ["a", "a", ""]
    assert_rows(code + "v = [S.n S.sum_x S.GroupCount];", [[1, 10, 1], [np.nan, 30, 1], [1, 20, 1]])
    assert_rows(
        "T = table({'a';'';'a'}, [1;1;NaN], [10;20;30], 'VariableNames', {'g','n','x'});"
        "S = groupsummary(T, {'g','n'}, 'sum', 'x', 'IncludeMissingGroups', false); v = [S.sum_x S.GroupCount];",
        [[10, 1]],
    )


def test_empty_category_and_undefined_group_stay_distinct():
    code = (
        "T = table(categorical({'a';'a';''}, {'a','b'}), [1;2;1], [10;20;30], 'VariableNames', {'g','n','x'});"
        "S = groupsummary(T, {'g','n'}, 'sum', 'x', 'IncludeEmptyGroups', true);"
    )
    s = run(code)
    assert s.workspace.get("S").cols[0].labels() == ["a", "a", "b", "b", "<undefined>"]
    assert_rows(code + "v = [S.n S.sum_x S.GroupCount];", [[1, 10, 1], [2, 20, 1], [1, 0, 0], [2, 0, 0], [1, 30, 1]])
    dropped = (
        "T = table(categorical({'a';'a';''}, {'a','b'}), [1;2;1], [10;20;30], 'VariableNames', {'g','n','x'});"
        "S = groupsummary(T, {'g','n'}, 'sum', 'x', 'IncludeEmptyGroups', true, 'IncludeMissingGroups', false);"
    )
    assert run(dropped).workspace.get("S").cols[0].labels() == ["a", "a", "b", "b"]


def test_missing_key_keeps_its_place_among_the_other_groups():
    # A missing value sorts last inside its own column. IncludeEmptyGroups must not
    # move that group to the end of the table.
    base = "T = table([1;1;2;2], [10;NaN;20;10], [1;2;3;4], 'VariableNames', {'A','B','y'});"
    without = base + "S = groupsummary(T, {'A','B'}, 'sum', 'y'); v = [S.A S.B S.sum_y];"
    with_empty = base + "S = groupsummary(T, {'A','B'}, 'sum', 'y', 'IncludeEmptyGroups', true); v = [S.A S.B S.sum_y S.GroupCount];"
    assert_rows(without, [[1, 10, 1], [1, np.nan, 2], [2, 10, 4], [2, 20, 3]])
    assert_rows(with_empty, [[1, 10, 1, 1], [1, 20, 0, 0], [1, np.nan, 2, 1], [2, 10, 4, 1], [2, 20, 3, 1]])
    present = rows(with_empty)[rows(with_empty)[:, 3] > 0][:, :3]
    assert np.allclose(present, rows(without), equal_nan=True)


def test_unobserved_numeric_combination_is_an_empty_group():
    code = (
        "T = table([1;1;2], [10;20;10], [1;2;3], 'VariableNames', {'a','b','x'});"
        "S = groupsummary(T, {'a','b'}, {'mean','sum'}, 'x', 'IncludeEmptyGroups', true);"
        "v = [S.a S.b S.GroupCount S.mean_x S.sum_x];"
    )
    assert_rows(code, [[1, 10, 1, 1, 1], [1, 20, 1, 2, 2], [2, 10, 1, 3, 3], [2, 20, 0, np.nan, 0]])


def test_logical_group_includes_the_absent_value():
    code = (
        "T = table([true;true], [1;3], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', {'mean','sum'}, 'x', 'IncludeEmptyGroups', true);"
    )
    s = run(code)
    assert np.asarray(s.workspace.get("S").cols[0].backend_buffer()).reshape(-1).tolist() == [False, True]
    assert_rows(code + "v = [S.GroupCount S.mean_x S.sum_x];", [[0, np.nan, 0], [2, 2, 4]])


def test_plain_numeric_group_adds_no_rows():
    # The pre-slice error sweep rejected this call. MATLAB returns the observed groups.
    code = "T = table([1;1;2], [4;5;6], 'VariableNames', {'g','x'});"
    assert_rows(
        code + "S = groupsummary(T, 'g', 'sum', 'x', 'IncludeEmptyGroups', true); v = [S.g S.sum_x S.GroupCount];",
        [[1, 9, 2], [2, 6, 1]],
    )
    assert_rows(
        code + "A = groupsummary(T, 'g', 'sum', 'x'); B = groupsummary(T, 'g', 'sum', 'x', 'IncludeEmptyGroups', 0);"
        "v = [A.sum_x B.sum_x];",
        [[9, 9], [6, 6]],
    )


def test_method_order_is_within_each_data_variable():
    code = (
        "T = table([1;1;2], [10;20;30], [3;5;7], 'VariableNames', {'g','x','y'});"
        "S = groupsummary(T, 'g', {'mean','sum'}, {'x','y'});"
        "v = S.Properties.VariableNames;"
    )
    got = [c.text for c in run(code).workspace.get("v").rows[0]]
    assert got == ["g", "GroupCount", "mean_x", "sum_x", "mean_y", "sum_y"]


def test_empty_table_with_categories_returns_one_row_per_category():
    code = (
        "T = table(categorical(cell(0,1), {'a','b'}), zeros(0,1), 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', {'mean','sum'}, 'x', 'IncludeEmptyGroups', true);"
    )
    s = run(code)
    assert s.workspace.get("S").cols[0].labels() == ["a", "b"]
    assert_rows(code + "v = [S.GroupCount S.mean_x S.sum_x];", [[0, np.nan, 0], [0, np.nan, 0]])


def test_empty_numeric_table_has_no_groups():
    assert_rows(
        "T = table(zeros(0,1), zeros(0,1), 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', 'sum', 'x', 'IncludeEmptyGroups', true); v = height(S);",
        [[0]],
    )
    assert_rows(
        "T = table(zeros(0,1), zeros(0,1), 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', 'sum', 'x'); v = height(S);",
        [[0]],
    )


def test_counts_only_when_no_method_is_given():
    code = (
        "T = table(categorical({'a';'b'}, {'a','b','c'}), [1;2], 'VariableNames', {'g','x'});"
        "S = groupsummary(T, 'g', 'IncludeEmptyGroups', true); v = [S.GroupCount' width(S)];"
    )
    assert_rows(code, [[1, 1, 0, 2]])


@pytest.mark.parametrize("code", [
    "groupsummary(table([1;1],[2;3]), 'Var1', 'numel')",
    "groupsummary(table([1;1],[2;3]), 'Var1', 'sum', 'IncludeEmptyGroups', 'yes')",
    "groupsummary(table([1;1],[2;3]), 'Var1', 'sum', 'IncludeEmptyGroups', [1 0])",
    "groupsummary(table([1;1],[2;3]), 'Var1', 'mean', 'Var2', 'IncludedEdge', 'right')",
    "groupsummary(table([1;1],[2;3]), 'Var1', 'mean', 'Var2', 'VariableNamingRule', 'fancy')",
    "groupsummary([1;2], [1], 'sum')",
])
def test_unsupported_groupsummary_inputs_are_matlab_errors(code):
    with pytest.raises(EvalError):
        run(code)
