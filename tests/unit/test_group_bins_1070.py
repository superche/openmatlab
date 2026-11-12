"""Calendar-width bins, datetime edges, and several schemes on one variable (#1070).

The four group* functions share ``_bin_columns``. Labels follow the discretize
categorical formats on the public page read 2026-11-07.
"""

from __future__ import annotations

import datetime as dt
import math
from fractions import Fraction

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


_SPAN = (
    "t = datetime([2016 12 31; 2017 1 1; 2017 6 1]);"
    "x = [1; 10; 4];"
    "T = table(t, x);"
)


def test_year_bins_follow_the_calendar_and_the_included_edge():
    code = _SPAN + "S = groupsummary(T, 't', 'year', 'sum', 'x');"
    s = run(code)
    assert s.workspace.get("S").names == ["year_t", "GroupCount", "sum_x"]
    assert s.workspace.get("S").cols[0].labels() == ["2016", "2017"]
    assert_rows(code + "v = [S.GroupCount S.sum_x];", [[1, 1], [2, 14]])
    # 2017-01-01 is the shared edge, so 'right' keeps it with 2016.
    right = _SPAN + "S = groupsummary(T, 't', 'year', 'sum', 'x', 'IncludedEdge', 'right');"
    assert run(right).workspace.get("S").cols[0].labels() == ["2016", "2017"]
    assert_rows(right + "v = [S.GroupCount S.sum_x];", [[2, 11], [1, 4]])
    # 2016-12-31 stays in 2016, including the leap day, rather than a 365.2425-day width.
    leap = (
        "t = datetime([2016 2 29; 2016 12 31; 2017 1 1]); x = [1; 2; 4]; T = table(t, x);"
        "S = groupsummary(T, 't', 'year', 'sum', 'x'); v = S.sum_x';"
    )
    assert_rows(leap, [[3, 4]])


def test_month_week_day_hour_quarter_and_decade_labels():
    months = (
        "t = datetime([2017 1 15; 2017 1 20; 2017 3 1]); x = [1; 2; 4]; T = table(t, x);"
        "S = groupsummary(T, 't', 'month', 'sum', 'x', 'IncludeEmptyGroups', true);"
    )
    assert run(months).workspace.get("S").cols[0].labels() == ["Jan-2017", "Feb-2017", "Mar-2017"]
    assert_rows(months + "v = [S.GroupCount S.sum_x];", [[2, 3], [0, 0], [1, 4]])
    # 24-Jan-2016 and 31-Jan-2016 are Sundays. The label is the week's first and last day.
    weeks = (
        "t = datetime([2016 1 24; 2016 1 31]); x = [1; 2]; T = table(t, x);"
        "S = groupsummary(T, 't', 'week', 'sum', 'x');"
    )
    assert run(weeks).workspace.get("S").cols[0].labels() == [
        "[24-Jan-2016, 30-Jan-2016)", "[31-Jan-2016, 06-Feb-2016]",
    ]
    assert_rows(weeks + "v = S.sum_x';", [[1, 2]])
    moved = weeks + "S = groupsummary(T, 't', 'week', 'sum', 'x', 'IncludedEdge', 'right');"
    assert run(moved).workspace.get("S").cols[0].labels() == ["[24-Jan-2016, 30-Jan-2016]"]
    assert_rows(moved + "v = S.sum_x;", [[3]])
    days = (
        "t = [datetime(2017,3,4,0,0,0); datetime(2017,3,4,23,0,0); datetime(2017,3,5,0,0,0)];"
        "T = table(t, [1; 2; 4], 'VariableNames', {'t','x'});"
        "S = groupsummary(T, 't', 'day', 'sum', 'x');"
    )
    assert run(days).workspace.get("S").cols[0].labels() == ["04-Mar-2017", "05-Mar-2017"]
    assert_rows(days + "v = S.sum_x';", [[3, 4]])
    hours = (
        "t = [datetime(2017,3,4,10,30,0); datetime(2017,3,4,10,59,0); datetime(2017,3,4,11,0,0)];"
        "T = table(t, [1; 2; 4], 'VariableNames', {'t','x'});"
        "S = groupsummary(T, 't', 'hour', 'sum', 'x');"
    )
    assert run(hours).workspace.get("S").cols[0].labels() == [
        "04-Mar-2017 10:00:00", "04-Mar-2017 11:00:00",
    ]
    quarters = (
        "t = datetime([2017 2 1; 2017 5 1]); T = table(t, [1; 2], 'VariableNames', {'t','x'});"
        "S = groupsummary(T, 't', 'quarter', 'sum', 'x');"
    )
    assert run(quarters).workspace.get("S").cols[0].labels() == ["Q1 2017", "Q2 2017"]
    decades = (
        "t = datetime([2016 6 1; 2021 1 1]); T = table(t, [1; 2], 'VariableNames', {'t','x'});"
        "S = groupsummary(T, 't', 'decade', 'sum', 'x');"
    )
    assert run(decades).workspace.get("S").cols[0].labels() == ["[2010, 2020)", "[2020, 2030]"]
    assert_rows(decades + "v = S.sum_x';", [[1, 2]])


def test_duration_width_and_calendar_duration_width():
    # days(1) is one fixed day. Multiples of that width are midnights, so membership matches
    # 'day', and the label is the interval rather than the named unit's point label.
    code = (
        "t = [datetime(2017,1,1,10,0,0); datetime(2017,1,2,9,0,0); datetime(2017,1,2,10,0,0)];"
        "x = [1; 2; 4]; T = table(t, x);"
    )
    named = run(code + "S = groupsummary(T, 't', 'day', 'sum', 'x');")
    assert named.workspace.get("S").names[0] == "day_t"
    assert named.workspace.get("S").cols[0].labels() == ["01-Jan-2017", "02-Jan-2017"]
    width = run(code + "S = groupsummary(T, 't', days(1), 'sum', 'x');")
    assert width.workspace.get("S").names[0] == "disc_t"
    assert width.workspace.get("S").cols[0].labels() == [
        "[01-Jan-2017, 02-Jan-2017)", "[02-Jan-2017, 03-Jan-2017]",
    ]
    assert_rows(code + "S = groupsummary(T, 't', days(1), 'sum', 'x'); v = S.sum_x';", [[1, 6]])
    # calmonths(1) starts at the first timestamp. 'month' starts at the first of the month.
    cal = (
        "t = datetime([2017 1 15; 2017 2 14; 2017 2 15]); x = [1; 2; 4]; T = table(t, x);"
        "S = groupsummary(T, 't', calmonths(1), 'sum', 'x');"
    )
    assert run(cal).workspace.get("S").cols[0].labels() == [
        "[15-Jan-2017, 15-Feb-2017)", "[15-Feb-2017, 15-Mar-2017]",
    ]
    assert_rows(cal + "v = S.sum_x';", [[3, 4]])
    # On a duration, 'hour' is a fixed hour from 0 and 'year' is 365.2425 days.
    hours = (
        "d = hours([0.5; 1.5; 3]); T = table(d, [1; 2; 4], 'VariableNames', {'d','x'});"
        "S = groupsummary(T, 'd', 'hour', 'sum', 'x');"
    )
    assert run(hours).workspace.get("S").names[0] == "hour_d"
    assert run(hours).workspace.get("S").cols[0].labels() == ["[0 hr, 1 hr)", "[1 hr, 2 hr)", "[3 hr, 4 hr]"]
    assert_rows(hours + "v = S.sum_x';", [[1, 2, 4]])
    years = (
        "d = days([0; 100; 400]); T = table(d, [1; 2; 4], 'VariableNames', {'d','x'});"
        "S = groupsummary(T, 'd', 'year', 'sum', 'x');"
    )
    assert run(years).workspace.get("S").cols[0].labels() == [
        "[0 days, 365.2 days)", "[365.2 days, 730.5 days]",
    ]
    same = (
        "d = days([0; 100; 400]); T = table(d, [1; 2; 4], 'VariableNames', {'d','x'});"
        "A = groupsummary(T, 'd', 'year', 'sum', 'x');"
        "B = groupsummary(T, 'd', calyears(1), 'sum', 'x');"
        "v = [A.sum_x' B.sum_x'];"
    )
    assert_rows(same, [[3, 4, 3, 4]])


def test_datetime_edges_use_discretize_intervals():
    code = (
        "edges = [datetime(2017,1,1) datetime(2017,6,1) datetime(2018,1,1)];"
        "t = [datetime(2017,1,15); datetime(2017,5,31); datetime(2017,6,1); datetime(2017,12,31); datetime(2018,1,1)];"
        "x = [1; 2; 4; 8; 16]; T = table(t, x);"
    )
    left = run(code + "S = groupsummary(T, 't', edges, 'sum', 'x');")
    assert left.workspace.get("S").names[0] == "disc_t"
    assert left.workspace.get("S").cols[0].labels() == [
        "[01-Jan-2017, 01-Jun-2017)", "[01-Jun-2017, 01-Jan-2018]",
    ]
    assert_rows(code + "S = groupsummary(T, 't', edges, 'sum', 'x'); v = [S.GroupCount S.sum_x];",
                [[2, 3], [3, 28]])
    right = code + "S = groupsummary(T, 't', edges, 'sum', 'x', 'IncludedEdge', 'right');"
    assert run(right).workspace.get("S").cols[0].labels() == [
        "[01-Jan-2017, 01-Jun-2017]", "(01-Jun-2017, 01-Jan-2018]",
    ]
    assert_rows(right + "v = S.sum_x';", [[7, 24]])
    outside = (
        "edges = [datetime(2017,1,1) datetime(2017,2,1)];"
        "t = [datetime(2016,12,31); datetime(2017,1,15)]; T = table(t, [1; 2], 'VariableNames', {'t','x'});"
        "S = groupsummary(T, 't', edges, 'sum', 'x');"
    )
    assert run(outside).workspace.get("S").cols[0].labels() == ["[01-Jan-2017, 01-Feb-2017]", "<undefined>"]
    assert_rows(outside + "v = S.sum_x';", [[2, 1]])


def test_several_schemes_on_one_variable_and_one_scheme_per_variable():
    two = (
        "t = datetime([2016 3 1; 2016 5 1; 2017 3 1]); x = [1; 2; 4]; T = table(t, x);"
        "S = groupsummary(T, 't', {'year','month'}, 'sum', 'x');"
    )
    s = run(two)
    assert s.workspace.get("S").names == ["year_t", "month_t", "GroupCount", "sum_x"]
    assert s.workspace.get("S").cols[0].labels() == ["2016", "2016", "2017"]
    assert s.workspace.get("S").cols[1].labels() == ["Mar-2016", "May-2016", "Mar-2017"]
    assert_rows(two + "v = S.sum_x';", [[1, 2, 4]])
    # A cell the same length as the grouping variables is still one scheme each.
    paired = (
        "g = [1; 1; 2; 2]; t = datetime([2016 1 1; 2016 5 1; 2017 1 1; 2017 2 1]);"
        "x = [10; 20; 30; 40]; T = table(g, t, x);"
        "S = groupsummary(T, {'g','t'}, {'none','year'}, 'sum', 'x');"
    )
    assert run(paired).workspace.get("S").names == ["g", "year_t", "GroupCount", "sum_x"]
    assert_rows(paired + "v = [S.g S.sum_x];", [[1, 30], [2, 70]])
    # Two edge vectors on one numeric variable. The second name takes the _1 suffix.
    edges = (
        "g = [1; 3; 4]; x = [10; 20; 30]; T = table(g, x);"
        "S = groupsummary(T, 'g', {[0 2 5],[0 10]}, 'sum', 'x');"
    )
    got = run(edges)
    assert got.workspace.get("S").names == ["disc_g", "disc_g_1", "GroupCount", "sum_x"]
    assert got.workspace.get("S").cols[0].labels() == ["[0, 2)", "[2, 5]"]
    assert got.workspace.get("S").cols[1].labels() == ["[0, 10]", "[0, 10]"]
    assert_rows(edges + "v = [S.GroupCount S.sum_x];", [[1, 10], [2, 50]])
    nested = (
        "g = [1; 3]; t = datetime([2016 3 1; 2017 5 1]); x = [10; 20]; T = table(g, t, x);"
        "S = groupsummary(T, {'g','t'}, {'none', {'year','month'}}, 'sum', 'x');"
    )
    assert run(nested).workspace.get("S").names == ["g", "year_t", "month_t", "GroupCount", "sum_x"]
    assert_rows(nested + "v = S.sum_x';", [[10, 20]])


def test_all_four_group_functions_share_the_year_bins():
    base = (
        "t = datetime([2016 1 1; 2016 6 1; 2017 1 1]);"
        "x = [1; 3; 10]; T = table(t, x);"
    )
    summary = run(base + "S = groupsummary(T, 't', 'year', 'sum', 'x');")
    assert summary.workspace.get("S").cols[0].labels() == ["2016", "2017"]
    counts = run(base + "C = groupcounts(T, 't', 'year');")
    assert counts.workspace.get("C").names == ["year_t", "GroupCount", "Percent"]
    assert counts.workspace.get("C").cols[0].labels() == ["2016", "2017"]
    assert_rows(base + "C = groupcounts(T, 't', 'year'); v = [C.GroupCount C.Percent];",
                [[2, 200 / 3], [1, 100 / 3]])
    transformed = run(base + "G = grouptransform(T, 't', 'year', 'meancenter', 'x');")
    assert transformed.workspace.get("G").names == ["t", "x", "year_t"]
    assert transformed.workspace.get("G").cols[2].labels() == ["2016", "2016", "2017"]
    assert_rows(base + "G = grouptransform(T, 't', 'year', 'meancenter', 'x'); v = G.x';", [[-1, 1, 0]])
    filtered = run(base + "G = groupfilter(T, 't', 'year', @(v) max(v) > 5);")
    assert filtered.workspace.get("G").names == ["t", "x", "year_t"]
    assert filtered.workspace.get("G").cols[2].labels() == ["2017"]
    assert_rows(base + "G = groupfilter(T, 't', 'year', @(v) max(v) > 5); v = G.x;", [[10]])
    # Array form: one grouping vector and two schemes come back as a row cell.
    wide = run(base + "[B,BG,BC] = groupsummary(x, t, {'year','month'}, 'sum');")
    assert wide.workspace.get("BG").shape == (1, 2)
    assert wide.workspace.get("BG").get(0, 0).labels() == ["2016", "2016", "2017"]
    assert wide.workspace.get("BG").get(0, 1).labels() == ["Jan-2016", "Jun-2016", "Jan-2017"]
    assert_rows(base + "[B,BG,BC] = groupsummary(x, t, {'year','month'}, 'sum'); v = [B BC];",
                [[1, 1], [3, 1], [10, 1]])
    counted = run(base + "[B,BG] = groupcounts(t, 'year');")
    assert counted.workspace.get("BG").labels() == ["2016", "2017"]
    assert_rows(base + "[B,BG] = groupcounts(t, 'year'); v = B;", [[2], [1]])


def test_missing_datetime_stays_its_own_group():
    code = (
        "t = [datetime(2017,3,1); NaT]; x = [5; 9]; T = table(t, x);"
        "S = groupsummary(T, 't', 'year', 'sum', 'x');"
    )
    assert run(code).workspace.get("S").cols[0].labels() == ["2017", "<undefined>"]
    assert_rows(code + "v = [S.GroupCount S.sum_x];", [[1, 5], [1, 9]])
    assert_rows(
        "t = [datetime(2017,3,1); NaT]; x = [5; 9]; T = table(t, x);"
        "S = groupsummary(T, 't', 'year', 'sum', 'x', 'IncludeMissingGroups', false); v = S.sum_x;",
        [[5]],
    )


def test_exact_boundaries_stay_in_the_closed_bin():
    # Repeated addition of 1/24 drifts off datetime(2017,1,1,2,0,0). IncludedEdge right
    # must keep 02:00 with 01:30, and 03:00 in the bin that ends at 03:00.
    hour = (
        "t = [datetime(2017,1,1,0,0,0); datetime(2017,1,1,1,30,0); "
        "datetime(2017,1,1,2,0,0); datetime(2017,1,1,3,0,0)];"
    )
    assert_rows(hour + "[B,BG] = groupcounts(t, 'hour', 'IncludedEdge', 'right'); v = B';", [[1, 2, 1]])
    assert run(hour + "[B,BG] = groupcounts(t, 'hour', 'IncludedEdge', 'right');").workspace.get("BG").labels() == [
        "01-Jan-2017 00:00:00", "01-Jan-2017 01:00:00", "01-Jan-2017 02:00:00",
    ]
    assert_rows(hour + "[B,BG] = groupcounts(t, 'hour', 'IncludedEdge', 'left'); v = B';", [[1, 1, 1, 1]])
    assert_rows(hour + "[B,BG] = groupcounts(t, hours(1), 'IncludedEdge', 'right'); v = B';", [[1, 2, 1]])
    # The same width anchored at 01:00, not at midnight. 02:00 and 05:00 are closed edges.
    assert_rows(
        "t = [datetime(2017,1,1,1,0,0); datetime(2017,1,1,2,0,0); datetime(2017,1,1,5,0,0)];"
        "[B,BG] = groupcounts(t, hours(1), 'IncludedEdge', 'right'); v = B';",
        [[2, 1]],
    )
    # The same edges on the shared path. 02:00 stays in the 01:00 bin, so its centered value
    # is grouped with 01:30.
    shared = (
        hour + "x = [1; 2; 4; 8]; T = table(t, x);"
        "S = groupsummary(T, 't', 'hour', 'sum', 'x', 'IncludedEdge', 'right');"
        "G = grouptransform(T, 't', 'hour', 'meancenter', 'x', 'IncludedEdge', 'right');"
    )
    assert_rows(shared + "v = S.sum_x';", [[1, 6, 8]])
    assert run(shared).workspace.get("G").cols[2].labels() == [
        "01-Jan-2017 00:00:00", "01-Jan-2017 01:00:00", "01-Jan-2017 01:00:00", "01-Jan-2017 02:00:00",
    ]
    # A duration stores n*(1/24). Cumulative edges miss hours(6) from below and hours(10) from above.
    assert_rows(
        "d = hours([0; 5.5; 6; 7]); [B,BG] = groupcounts(d, hours(1), 'IncludedEdge', 'right'); v = B';",
        [[1, 2, 1]],
    )
    assert_rows(
        "d = hours([0; 9.5; 10; 11]); [B,BG] = groupcounts(d, 'hour', 'IncludedEdge', 'left'); v = B';",
        [[1, 1, 1, 1]],
    )
    # Minute and second edges are clock times, not a running sum of 1/1440 or 1/86400.
    assert_rows(
        "t = [datetime(2017,1,1,10,59,0); datetime(2017,1,1,11,0,0); datetime(2017,1,1,11,0,30)];"
        "[B,BG] = groupcounts(t, 'minute', 'IncludedEdge', 'right'); v = B';",
        [[2, 1]],
    )
    seconds = (
        "t = [datetime(2017,1,1,10,0,0); datetime(2017,1,1,10,1,4); datetime(2017,1,1,10,1,5)];"
        "[B,BG] = groupcounts(t, 'second', 'IncludedEdge', 'left');"
    )
    assert run(seconds).workspace.get("BG").labels() == [
        "01-Jan-2017 10:00:00", "01-Jan-2017 10:01:04", "01-Jan-2017 10:01:05",
    ]


def test_day_offset_is_not_a_datetime_component():
    """7681 half-seconds after midnight is 01:04:00.5 in real arithmetic, and not as a datenum.

    ``midnight + n * width`` and ``datenum_from_parts`` are different floats. Datetime edges have
    to use the component formula. This locks that fact so a later change does not treat them as
    interchangeable.
    """
    from openmatlab.runtime.objects import datenum_from_parts

    midnight = datenum_from_parts(2017, 1, 1)
    width = 0.5 / 86400.0
    # 01:04:00.5 is 7681 half-seconds after midnight. The day offset is one ulp above the component.
    assert midnight + 7681 * width != datenum_from_parts(2017, 1, 1, 1, 4, 0.5)
    # Anchoring the same width at the previous grid point and adding one step misses 23:59:00.5.
    anchor = math.floor(datenum_from_parts(2017, 1, 1, 23, 59, 0) / width) * width
    assert anchor + width != datenum_from_parts(2017, 1, 1, 23, 59, 0.5)


def test_fractional_second_edges_match_datetime_components():
    # Right edge: 23:59:00, 00.25 and 00.5 share the bin that closes on 00.5. The next second
    # is its own bin. Day-offset edges put 00.5 into the following bin.
    right = (
        "t = [datetime(2017,1,1,23,59,0); datetime(2017,1,1,23,59,0.25); "
        "datetime(2017,1,1,23,59,0.5); datetime(2017,1,1,23,59,1)];"
        "x = [1; 2; 4; 8]; T = table(t, x);"
    )
    assert_rows(right + "[B,BG] = groupcounts(t, seconds(0.5), 'IncludedEdge', 'right'); v = B';", [[3, 1]])
    # The boundary row stays with the two earlier rows, so the group sum is 7 and the last row drops.
    kept = run(right + "G = groupfilter(T, 't', seconds(0.5), @(v) sum(v) == 7, 'IncludedEdge', 'right');")
    assert_rows(right + "G = groupfilter(T, 't', seconds(0.5), @(v) sum(v) == 7, 'IncludedEdge', 'right'); v = G.x';",
                [[1, 2, 4]])
    assert kept.workspace.get("G").shape[0] == 3
    # Left edge, not at midnight: 01:04:00 and 00.25, then 00.5 alone, then 1 alone.
    assert_rows(
        "t = [datetime(2017,1,1,1,4,0); datetime(2017,1,1,1,4,0.25); "
        "datetime(2017,1,1,1,4,0.5); datetime(2017,1,1,1,4,1)];"
        "[B,BG] = groupcounts(t, seconds(0.5)); v = B';",
        [[2, 1, 1]],
    )
    # The half-second grid crosses midnight. 23:59:59.5 is the right edge of its bin; 00:00 is the next.
    assert_rows(
        "t = [datetime(2017,1,1,23,59,59); datetime(2017,1,1,23,59,59.5); datetime(2017,1,2,0,0,0)];"
        "[B,BG] = groupcounts(t, seconds(0.5), 'IncludedEdge', 'right'); v = B';",
        [[2, 1]],
    )
    # A duration stores n*unit, so its edges stay on that product, including a half-second width.
    assert_rows(
        "d = seconds([0; 0.25; 0.5; 1]); [B,BG] = groupcounts(d, seconds(0.5), 'IncludedEdge', 'right'); v = B';",
        [[3, 1]],
    )
    assert_rows(
        "d = seconds([0; 0.25; 0.5; 1]); [B,BG] = groupcounts(d, seconds(0.5)); v = B';",
        [[2, 1, 1]],
    )


def _dt_call(y, mo, d, h, mi, s):
    return f"datetime({y},{mo},{d},{h},{mi},{s!r})"


def _groupcounts(points, width, which):
    vec = "; ".join(points)
    return (
        f"t = [{vec}]; [B,BG] = groupcounts(t, seconds({width!r}), "
        f"'IncludedEdge', '{which}'); v = B';"
    )


def _assert_component_neighbors(lo, boundary, hi, width_s):
    """``boundary`` is an exact edge. One ulp below and one ulp above stay on their own sides."""
    from openmatlab.libs.table_join_group import _codes_for_edges, _component_edges

    edges = _component_edges(lo, hi, width_s * (1.0 / 86400.0), "groupcounts")
    assert any(float(edge) == boundary for edge in edges)
    assert float(edges[0]) < boundary < float(edges[-1])
    down = np.nextafter(boundary, -np.inf)
    up = np.nextafter(boundary, np.inf)
    assert down != boundary and up != boundary
    left = _codes_for_edges(np.array([down, boundary, up]), edges, "left")
    right = _codes_for_edges(np.array([down, boundary, up]), edges, "right")
    # Left closes on the left edge: the boundary opens the next bin, and the ulp above stays there.
    assert left.tolist() == [left[0], left[0] + 1, left[0] + 1]
    # Right closes on the right edge: the ulp below stays with the boundary, and the ulp above leaves.
    assert right.tolist() == [right[0], right[0], right[0] + 1]
    assert int(left[0]) != 0 and int(right[0]) != 0


def test_absolute_epoch_rational_is_not_the_millisecond_component():
    """``Fraction(0.001)`` times the epoch step index is not ``datetime(..., 0.001)``.

    The float width round-trips (``width * 86400 == 0.001``), and that product is the rational
    ``1152921504606847/1152921504606846976``. Multiplying by the absolute index
    ``63650534400001`` moves the seconds field by about 1.3 microseconds, which is one datenum
    ulp. A local step of ``0.001`` is the component. This is the representation fact; it does
    not depend on the binning function.
    """
    from openmatlab.runtime.objects import datenum_from_parts, parts_from_datenum

    component = datenum_from_parts(2017, 1, 1, 0, 0, 0.001)
    width = 0.001 * (1.0 / 86400.0)
    width_s = Fraction(float(width) * 86400.0)
    assert width_s == Fraction(0.001)
    assert width_s == Fraction(1152921504606847, 1152921504606846976)
    k = 736696 * 86_400_000 + 1
    assert k == 63_650_534_400_001
    total = width_s * k
    day = int(total // 86400)
    sod = total - day * 86400
    whole = int(sod)
    frac = float(sod - whole)
    hh, rem = divmod(whole, 3600)
    mm, ss = divmod(rem, 60)
    y, mo, d = parts_from_datenum(float(day))[:3]
    epoch_edge = datenum_from_parts(y, mo, d, hh, mm, ss + frac)
    assert epoch_edge == np.nextafter(component, np.inf)
    assert epoch_edge != component
    assert datenum_from_parts(2017, 1, 1, 0, 0, 0.001) == component
    assert datenum_from_parts(2017, 1, 1, 0, 0, 2 * 0.001) == datenum_from_parts(2017, 1, 1, 0, 0, 0.002)


def test_millisecond_left_edge_keeps_the_boundary_in_its_own_bin():
    # 0 and 0.0005 share the bin that opens at midnight. 0.001 opens the next bin. 0.002 opens
    # the one after. The epoch edge sits one ulp above 0.001, which pulls 0.001 back into the
    # first bin and returns [3; 1].
    code = (
        "t = [datetime(2017,1,1,0,0,0); datetime(2017,1,1,0,0,0.0005); "
        "datetime(2017,1,1,0,0,0.001); datetime(2017,1,1,0,0,0.002)];"
        "x = [1; 2; 4; 8]; T = table(t, x);"
    )
    assert_rows(
        code + "[B,BG] = groupcounts(t, seconds(0.001), 'IncludedEdge', 'left'); v = B';",
        [[2, 1, 1]],
    )
    assert_rows(
        code + "[B,BG] = groupcounts(t, seconds(0.001), 'IncludedEdge', 'right'); v = B';",
        [[3, 1]],
    )
    kept = run(
        code + "G = groupfilter(T, 't', seconds(0.001), @(v) sum(v) == 3, 'IncludedEdge', 'left');"
    )
    assert kept.workspace.get("G").shape[0] == 2
    assert_rows(
        code + "G = groupfilter(T, 't', seconds(0.001), @(v) sum(v) == 3, 'IncludedEdge', 'left'); v = G.x';",
        [[1, 2]],
    )
    from openmatlab.runtime.objects import datenum_from_parts

    _assert_component_neighbors(
        datenum_from_parts(2017, 1, 1),
        datenum_from_parts(2017, 1, 1, 0, 0, 0.001),
        datenum_from_parts(2017, 1, 1, 0, 0, 0.002),
        0.001,
    )


_NONBINARY_WIDTHS = [0.001, 0.01, 0.1, 0.2]
_ANCHORS = [
    (2017, 1, 1, 0, 0),
    (2016, 2, 29, 10, 0),
    (1999, 7, 15, 3, 30),
    (2020, 12, 31, 22, 15),
]
_ROLLOVER_DAYS = [(2017, 1, 1), (2016, 2, 29), (2020, 12, 31)]


@pytest.mark.parametrize("width", _NONBINARY_WIDTHS)
@pytest.mark.parametrize("anchor", _ANCHORS)
@pytest.mark.parametrize("which", ["left", "right"])
def test_nonbinary_widths_match_component_boundaries(width, anchor, which):
    y, mo, d, h, mi = anchor
    points = [_dt_call(y, mo, d, h, mi, s) for s in (0.0, width / 2, width, 2 * width)]
    expected = [[2, 1, 1]] if which == "left" else [[3, 1]]
    assert_rows(_groupcounts(points, width, which), expected)
    from openmatlab.runtime.objects import datenum_from_parts

    _assert_component_neighbors(
        datenum_from_parts(y, mo, d, h, mi, 0),
        datenum_from_parts(y, mo, d, h, mi, width),
        datenum_from_parts(y, mo, d, h, mi, 2 * width),
        width,
    )


@pytest.mark.parametrize("width", _NONBINARY_WIDTHS)
@pytest.mark.parametrize("day", _ROLLOVER_DAYS)
@pytest.mark.parametrize("which", ["left", "right"])
def test_nonbinary_widths_roll_over_midnight(width, day, which):
    y, mo, d = day
    nxt = dt.date(y, mo, d) + dt.timedelta(days=1)
    points = [
        _dt_call(y, mo, d, 23, 59, 60 - width),
        _dt_call(nxt.year, nxt.month, nxt.day, 0, 0, 0),
        _dt_call(nxt.year, nxt.month, nxt.day, 0, 0, width / 2),
    ]
    # Left: the last step of the day opens its own bin; midnight and the half-step share the next.
    # Right: the last step and midnight close one bin; the half-step opens the next.
    expected = [[1, 2]] if which == "left" else [[2, 1]]
    assert_rows(_groupcounts(points, width, which), expected)
    from openmatlab.runtime.objects import datenum_from_parts

    _assert_component_neighbors(
        datenum_from_parts(y, mo, d, 23, 59, 60 - width),
        datenum_from_parts(nxt.year, nxt.month, nxt.day),
        datenum_from_parts(nxt.year, nxt.month, nxt.day, 0, 0, width),
        width,
    )


def test_duration_millisecond_width_stays_on_the_scaled_grid():
    assert_rows(
        "d = seconds([0; 0.0005; 0.001; 0.002]);"
        "[B,BG] = groupcounts(d, seconds(0.001), 'IncludedEdge', 'left'); v = B';",
        [[2, 1, 1]],
    )
    assert_rows(
        "d = seconds([0; 0.0005; 0.001; 0.002]);"
        "[B,BG] = groupcounts(d, seconds(0.001), 'IncludedEdge', 'right'); v = B';",
        [[3, 1]],
    )


@pytest.mark.parametrize("code", [
    "groupsummary(table([1;2],[3;4],'VariableNames',{'g','x'}), 'g', 'week', 'sum', 'x')",
    "groupsummary(table(days([1;2]), [3;4], 'VariableNames', {'d','x'}), 'd', 'week', 'sum', 'x')",
    "groupsummary(table([1;2],[3;4],'VariableNames',{'g','x'}), 'g', datetime(2017,1,[1 2]), 'sum', 'x')",
    "groupsummary(table(datetime(2017,1,1), 1), 'Var1', days([1 2]), 'sum')",
    "groupsummary(table(datetime(2017,1,1), 1), 'Var1', days(0), 'sum')",
    "groupsummary(table(datetime(2017,1,1), 1), 'Var1', calmonths(0), 'sum')",
    "T = table([1;1;2],[3;4;5],[6;7;8],'VariableNames',{'a','b','x'});"
    " groupsummary(T, {'a','b'}, {'year','month','day'}, 'sum', 'x')",
])
def test_bin_mismatches_are_eval_errors(code):
    with pytest.raises(EvalError):
        run(code)
