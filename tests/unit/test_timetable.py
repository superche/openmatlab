"""timetable (Epic #697, M10 T10)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]

TT = "t = datetime(2020,1,1) + hours(0:5)'; x = (1:6)'; TT = timetable(t, x); "
D = "D = timetable(seconds([0;1;2;3]), [1;2;3;4], 'VariableNames', {'v'}); "


def run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def num(code, name="v"):
    return np.asarray(run(code).workspace.get(name).backend_buffer(), float).tolist()


def test_construct_size_class_and_dimname():
    s = run(TT + "c = class(TT); h = height(TT); w = width(TT); a = istimetable(TT); b = istable(TT); "
                 "d = TT.Properties.DimensionNames;")
    ws = s.workspace
    assert ws.get("c").text == "timetable"
    assert num(TT + "v = [height(TT) width(TT) istimetable(TT) istable(TT)];") == [[6, 1, 1, 0]]
    assert [e.text for e in ws.get("d").rows[0]] == ["t", "Variables"]


def test_rowtimes_access_and_display():
    s = run(TT + "r = TT.t(3);")
    assert "02:00:00" in s.workspace.get("r").display_text()
    txt = run(TT).workspace.get("TT").display_text()
    assert "6×1 timetable" in txt and "01-Jan-2020 00:00:00" in txt  # one format for the column


def test_time_subscripts():
    assert num(TT + "v = TT{datetime(2020,1,1,2,0,0), 'x'};") == [[3]]
    assert num(TT + "S = TT(timerange(datetime(2020,1,1,1,0,0), datetime(2020,1,1,3,0,0)), :); v = S.x';") == [[2, 3]]
    assert num(TT + "S = TT(timerange(datetime(2020,1,1,1,0,0), datetime(2020,1,1,3,0,0), 'closed'), :); v = S.x';") == [[2, 3, 4]]
    assert num(TT + "S = TT(timerange('2020-01-01 01:00:00', '2020-01-01 02:00:00', 'openleft'), :); v = S.x';") == [[3]]
    assert num(TT + "S = TT(withtol(datetime(2020,1,1,2,10,0), minutes(15)), :); v = S.x;") == [[3]]
    assert num(TT + "S = TT(datetime(2030,1,1), :); v = height(S);") == [[0]]


def test_retime():
    assert num(TT + "R = retime(TT, 'regular', 'mean', 'TimeStep', hours(2)); v = R.x';") == [[1.5, 3.5, 5.5]]
    assert num(TT + "R = retime(TT, 'regular', 'sum', 'TimeStep', hours(3)); v = R.x';") == [[6, 15]]
    assert num(D + "R = retime(D, seconds([0.5;2.5]), 'previous'); v = R.v';") == [[1, 3]]
    assert num(D + "R = retime(D, seconds([0.5;2.5]), 'next'); v = R.v';") == [[2, 4]]
    assert num(D + "R = retime(D, seconds([0.5;2.5]), 'linear'); v = R.v';") == [[1.5, 3.5]]
    r = num(D + "R = retime(D, seconds([0.5;1]), 'fillwithmissing'); v = R.v';")
    assert np.isnan(r[0][0]) and r[0][1] == 2
    assert num(D + "R = retime(D, 'secondly', 'count'); v = R.v';") == [[1, 1, 1, 1]]


def test_synchronize_and_lag():
    code = (TT + "B = timetable(datetime(2020,1,1) + hours([0;2]), [10;20], 'VariableNames', {'y'}); "
            "Y = synchronize(TT(1:3,:), B, 'union', 'previous');")
    assert num(code + "v = Y.y';") == [[10, 10, 20]]
    assert num(code + "v = width(Y);") == [[2]]
    s = run("A = timetable(hours([0;1]), [1;2], 'VariableNames', {'v'}); "
            "B = timetable(hours([0;2]), [5;6], 'VariableNames', {'v'}); Y = synchronize(A, B);")
    assert s.workspace.get("Y").names == ["v_A", "v_B"]
    r = num(D + "L = lag(D, 2); v = L.v';")
    assert np.isnan(r[0][0]) and np.isnan(r[0][1]) and r[0][2:] == [1, 2]
    r = num(D + "L = lag(D, seconds(-1)); v = L.v';")
    assert r[0][:3] == [2, 3, 4] and np.isnan(r[0][3])


def test_conversions_concat_growth():
    assert num(TT + "T = table(t, x); TT2 = table2timetable(T); v = [width(TT2) istimetable(TT2)];") == [[1, 1]]
    assert num(TT + "T = timetable2table(TT); v = [width(T) istable(T)];") == [[2, 1]]
    assert num(D + "E = [D; D]; v = height(E);") == [[8]]
    s = run(D + "D(5,:) = {9};")
    rt = s.workspace.get("D").rowtimes.v.reshape(-1)
    assert np.isnan(rt[4])
    assert num(D + "D.w = D.v * 2; v = D.w';") == [[2, 4, 6, 8]]


@pytest.mark.parametrize("code", [
    "timetable([1;2])",
    "table2timetable(table([1;2]))",
    "withtol(seconds(1), 3)",
    "timerange(1, 2)",
    D + "retime(D, 'regular', 'mean')",
    D + "retime(D, 'fortnightly', 'mean')",
    D + "retime(D, 'secondly', 'bogus')",
    "retime(timetable(seconds([0;1]), {'a';'b'}), 'secondly', 'mean')",
    "lag(timetable(seconds([0;1;3]), [1;2;3]), seconds(1))",
    "synchronize(timetable(seconds(0), 1), timetable(datetime(2020,1,1), 2))",
])
def test_errors_are_matlab_errors(code):
    with pytest.raises(EvalError):
        run(code)
