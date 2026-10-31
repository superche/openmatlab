"""ismissing, rmmissing, and fillmissing constant/previous/next (M17, #1033)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.cli import main
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session
from openmatlab.runtime.string_array import StringArray

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _n(ws, name):
    return _buf(ws.get(name))


def _buf(v):
    return np.asarray(v.backend_buffer())


def _strings(v):
    if isinstance(v, StringArray):
        return v.data.tolist()
    return [[v.text]]


def test_vector_three_methods_and_removal():
    ws = _ws(
        "p = fillmissing([1 3 NaN 4 NaN NaN 5], 'previous');"
        "n = fillmissing([NaN 1 NaN 3], 'next');"
        "c = fillmissing([NaN 1 NaN], 'constant', 0);"
        "m = ismissing([1 NaN 3]);"
        "[r, tf] = rmmissing([1 NaN 3 NaN 5]);"
        "[f, filled] = fillmissing([NaN 1 NaN], 'previous');"
    )
    assert _n(ws, "p").tolist() == [[1, 3, 3, 4, 4, 4, 5]]
    assert _n(ws, "n").tolist() == [[1, 1, 3, 3]]
    assert _n(ws, "c").tolist() == [[0, 1, 0]]
    assert _n(ws, "m").dtype == bool and _n(ws, "m").tolist() == [[False, True, False]]
    assert _n(ws, "r").tolist() == [[1, 3, 5]] and _n(ws, "r").shape == (1, 3)
    assert _n(ws, "tf").tolist() == [[False, True, False, True, False]]
    # leading gap stays missing, so it is not reported as filled
    assert np.isnan(_n(ws, "f")[0, 0]) and _n(ws, "f")[0, 1:].tolist() == [1, 1]
    assert _n(ws, "filled").tolist() == [[False, False, True]]


def test_column_vector_and_matrix_dimension():
    ws = _ws(
        "c = fillmissing([1; NaN; 3], 'previous');"
        "rc = rmmissing([1; NaN; 3]);"
        "A = [1 NaN 3; NaN 5 NaN];"
        "down = fillmissing(A, 'previous');"
        "across = fillmissing(A, 'previous', 2);"
        "cols = fillmissing([1 NaN; NaN 2], 'constant', [100 1000]);"
    )
    assert _n(ws, "c").tolist() == [[1], [1], [3]] and _n(ws, "rc").tolist() == [[1], [3]]
    down = _n(ws, "down")
    assert [down[0, 0], down[0, 2]] == [1, 3] and np.isnan(down[0, 1]) and down[1].tolist() == [1, 5, 3]
    assert np.isnan(_n(ws, "across")[1, 0]) and _n(ws, "across")[0].tolist() == [1, 1, 3]
    assert _n(ws, "across")[1, 1:].tolist() == [5, 5]
    assert _n(ws, "cols").tolist() == [[1, 1000], [100, 2]]


def test_logical_and_integer_have_no_missing_values():
    ws = _ws(
        "a = [true false true]; m = ismissing(a); r = rmmissing(a); f = fillmissing(a, 'next');"
        "k = int16([1 2 3]); mk = ismissing(k); rk = rmmissing(k);"
    )
    assert _n(ws, "m").tolist() == [[False, False, False]]
    assert _n(ws, "r").tolist() == [[True, False, True]] and _n(ws, "f").tolist() == _n(ws, "r").tolist()
    assert ws.get("r").matlab_class() == "logical" and ws.get("rk").matlab_class() == "int16"
    assert _n(ws, "mk").tolist() == [[False, False, False]] and _n(ws, "rk").tolist() == [[1, 2, 3]]


def test_string_vector_and_table():
    ws = _ws(
        "p = fillmissing([\"a\" missing \"c\" missing], 'previous');"
        "n = fillmissing([missing \"b\" missing], 'next');"
        "c = fillmissing([\"a\" missing \"c\"], 'constant', \"z\");"
        "r = rmmissing([\"a\" missing \"c\"]);"
        "T = table([1; NaN; 3], [\"a\"; missing; \"c\"], 'VariableNames', {'x','s'}, 'RowNames', {'r1','r2','r3'});"
        "M = ismissing(T); P = fillmissing(T, 'previous'); N = fillmissing(T, 'next');"
        "C = fillmissing(T, 'constant', 0, 'DataVariables', 'x'); R = rmmissing(T);"
    )
    assert _strings(ws.get("p")) == [["a", "a", "c", "c"]]
    assert _strings(ws.get("n")) == [["b", "b", None]]
    assert _strings(ws.get("c")) == [["a", "z", "c"]]
    assert _strings(ws.get("r")) == [["a", "c"]]
    assert _n(ws, "M").tolist() == [[False, False], [True, True], [False, False]]
    assert _buf(ws.get("P").cols[0]).tolist() == [[1], [1], [3]]
    assert _strings(ws.get("P").cols[1]) == [["a"], ["a"], ["c"]]
    assert _strings(ws.get("N").cols[1]) == [["a"], ["c"], ["c"]]
    assert _buf(ws.get("N").cols[0]).tolist() == [[1], [3], [3]]
    assert _buf(ws.get("C").cols[0]).tolist() == [[1], [0], [3]]
    assert _strings(ws.get("C").cols[1]) == [["a"], [None], ["c"]]
    assert ws.get("R").rownames == ["r1", "r3"] and ws.get("R").nrows == 2


def test_table_previous_on_categorical_and_cellstr():
    ws = _ws(
        "A = table(categorical({'Sunny'; 'Cloudy'; ''}), [66; NaN; 54], {''; 'N'; 'Y'}, [37; 39; NaN], "
        "'VariableNames', {'Description','Temperature','Rain','Humidity'});"
        "F = fillmissing(A, 'previous');"
        "Z = fillmissing(A, 'constant', 0, 'DataVariables', {'Temperature','Humidity'});"
    )
    f = ws.get("F")
    assert f.cols[0].labels() == ["Sunny", "Cloudy", "Cloudy"]
    assert _buf(f.cols[1]).tolist() == [[66], [66], [54]]
    assert [f.cols[2].rows[i][0].text for i in range(3)] == ["", "N", "Y"]
    assert _buf(f.cols[3]).tolist() == [[37], [39], [39]]
    z = ws.get("Z")
    assert z.cols[0].labels()[2] == "<undefined>"
    assert _buf(z.cols[1]).tolist() == [[66], [0], [54]]
    assert _buf(z.cols[3]).tolist() == [[37], [39], [0]]


def test_min_num_missing_and_empty_removal():
    ws = _ws(
        "R = rmmissing([1 NaN; NaN NaN; 3 4], 'MinNumMissing', 2);"
        "E = rmmissing(table([NaN; NaN], 'VariableNames', {'x'})); h = height(E);"
    )
    got = _n(ws, "R")
    assert got.shape == (2, 2) and got[0, 0] == 1 and np.isnan(got[0, 1]) and got[1].tolist() == [3, 4]
    assert _n(ws, "h").tolist() == [[0]]


def test_timetable_keeps_its_class():
    ws = _ws(
        "D = timetable(seconds([0;1;2]), [1; NaN; 3], 'VariableNames', {'v'});"
        "F = fillmissing(D, 'previous'); R = rmmissing(D); fv = F.v; rv = R.v; cf = class(F); cr = class(R);"
    )
    assert ws.get("cf").text == "timetable" and ws.get("cr").text == "timetable"
    assert _n(ws, "fv").tolist() == [[1], [1], [3]] and _n(ws, "rv").tolist() == [[1], [3]]


def test_unsupported_method_and_option_are_matlab_errors():
    cases = [
        ("fillmissing([1 NaN], 'movmean', 3)", "movmean", "OpenMATLAB:fillmissing:UnsupportedMethod"),
        ("fillmissing([1 NaN 3], 'linear')", "linear", "OpenMATLAB:fillmissing:UnsupportedMethod"),
        ("fillmissing([1 NaN], 'banana')", "banana", "OpenMATLAB:fillmissing:InvalidMethod"),
        ("fillmissing([1 NaN], 'constant')", "fill value", "OpenMATLAB:fillmissing:ConstantValueRequired"),
        ("fillmissing([1 NaN], 'previous', 'EndValues', 'nearest')", "EndValues", "OpenMATLAB:fillmissing:UnsupportedOption"),
        ("ismissing([1 NaN], -99)", "indicator", "OpenMATLAB:ismissing:Indicator"),
    ]
    for code, text, ident in cases:
        with pytest.raises(EvalError) as ei:
            _ws(code)
        msg = str(ei.value)
        assert text in msg and "Traceback" not in msg
        assert ei.value.identifier == ident


def test_cli_eval_and_unsupported_method(capsys):
    with pytest.raises(SystemExit) as ok:
        main(["-e", "fillmissing([1 NaN 3], 'next');"])
    assert ok.value.code == 0
    assert "Traceback" not in capsys.readouterr().err
    with pytest.raises(SystemExit) as bad:
        main(["-e", "fillmissing([1 NaN], 'movmean', 3);"])
    assert bad.value.code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err and "movmean" in err and "constant" in err
