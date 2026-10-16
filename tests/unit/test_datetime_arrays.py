"""datetime/duration arrays, calendarDuration, dateshift, between (Epic #695, M10 T09)."""

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


def num(code, name="v"):
    return np.asarray(run(code).workspace.get(name).backend_buffer(), float).tolist()


def text(code, name="v"):
    v = run(code).workspace.get(name)
    if getattr(v, "is_string", False):
        return [str(x) for x in np.asarray(v.data).reshape(-1)]
    return v.text


def test_column_vector_transpose_and_concat():
    assert num("t = datetime(2020,1,1) + days(0:2)'; v = size(t);") == [[3, 1]]
    assert num("t = datetime(2020,1,1) + days(0:2); v = size(t');") == [[3, 1]]
    assert num("v = size([datetime(2020,1,1); datetime(2021,1,1); NaT]);") == [[3, 1]]
    assert num("c = [datetime(2020,1,1) '2021-06-15']; v = c(2).Month;") == [[6]]
    assert num("v = size([NaT, []]);") == [[1, 1]]


def test_nat_and_isnat():
    assert num("v = isnat([datetime(2020,1,1) NaT]);") == [[0, 1]]
    assert num("v = size(NaT(2,3));") == [[2, 3]]
    assert num("v = isnat(datetime([\"2020-01-01\"; \"NaT\"]));") == [[0], [1]]


def test_inputformat_and_format():
    assert num("d = datetime('15/03/2021','InputFormat','dd/MM/yyyy'); v = [d.Year d.Month d.Day];") == [[2021, 3, 15]]
    assert text("d = datetime('15/03/2021','InputFormat','dd/MM/yyyy'); v = char(d);") == "15/03/2021"
    assert text("d = datetime(2021,3,15); d.Format = 'yyyy-MM-dd'; v = char(d);") == "2021-03-15"
    assert text("d = datetime(2020,1,1,15,4,5,'Format','MMM d, yyyy h:mm a'); v = char(d);") == "Jan 1, 2020 3:04 PM"
    assert num("d = datetime({'01/02/2020','03/04/2021'},'InputFormat','dd/MM/yyyy'); v = d.Month;") == [[2, 4]]


def test_default_format_is_uniform_across_elements():
    assert text("v = string([datetime(2020,1,1); datetime(2020,1,2,3,4,5)]);") == [
        "01-Jan-2020 00:00:00", "02-Jan-2020 03:04:05"]


def test_component_assignment_rolls_over():
    assert num("x = datetime(2023,1,1); x.Month = 14; v = [x.Year x.Month];") == [[2024, 2]]
    assert num("x = datetime(2020,1,31); x.Day = 32; v = [x.Month x.Day];") == [[2, 1]]
    assert num("x = datetime(2020,3,1); x.Month = 0; v = [x.Year x.Month];") == [[2019, 12]]
    assert num("x = [datetime(2020,1,1) NaT]; x.Day = 5; v = x.Day;")[0][0] == 5


def test_dateshift():
    assert num("s = dateshift(datetime(2021,3,15,10,30,0),'start','month'); v = [s.Day s.Hour];") == [[1, 0]]
    assert num("e = dateshift(datetime(2021,2,10),'end','month'); v = e.Day;") == [[28]]
    assert num("e = dateshift(datetime(2020,2,10),'end','quarter'); v = [e.Month e.Day];") == [[3, 31]]
    assert num("e = dateshift(datetime(2021,3,15),'start','month','next'); v = e.Month;") == [[4]]
    assert num("e = dateshift(datetime(2021,3,15),'start','year',-1); v = e.Year;") == [[2020]]
    assert num("e = dateshift(datetime(2026,10,16),'start','week'); v = e.Day;") == [[11]]  # Sunday


def test_between_and_split():
    assert num("b = between(datetime(2020,1,15), datetime(2020,3,20), 'days'); v = split(b,'days');") == [[65]]
    assert num("b = between(datetime(2020,1,15), datetime(2021,3,20)); [y,m,d] = split(b,{'years','months','days'}); v = [y m d];") == [[1, 2, 5]]
    assert num("b = between(datetime(2021,3,20), datetime(2020,1,15), 'months'); v = split(b,'months');") == [[-14]]
    assert num("[h,m] = split(minutes(150), {'hours','minutes'}); v = [h m];") == [[2, 30]]


def test_calendar_arithmetic_clamps_month_end():
    assert num("m = datetime(2020,1,31) + calmonths(1); v = [m.Month m.Day];") == [[2, 29]]
    assert num("m = datetime(2020,3,31) - calmonths(1); v = [m.Month m.Day];") == [[2, 29]]
    assert num("p = datetime(2020,1,1) + caldays(10); v = p.Day;") == [[11]]
    assert num("p = calyears(1) + datetime(2020,2,29); v = [p.Year p.Month p.Day];") == [[2021, 2, 28]]
    assert num("c = calendarDuration(1,2,3); p = datetime(2020,1,1) + c; v = [p.Year p.Month p.Day];") == [[2021, 3, 4]]


def test_calendar_duration_display():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("c = [calmonths(14) caldays(2) calendarDuration(0,0,0,1,30,0)];")
    assert s.workspace.get("c").display_text().split() == ["1y", "2mo", "2d", "1h", "30m"]


@pytest.mark.parametrize("code", [
    "datetime('2021-13-45','InputFormat','yyyy-MM-dd')",
    "datetime(5,'InputFormat','yyyy')",
    "datetime(2020,1,1,'TimeZone','UTC')",
    "[datetime(2020,1,1) days(1)]",
    "[days(1) 5]",
    "dateshift(5,'start','month')",
    "dateshift(datetime(2020,1,1),'mid','month')",
    "dateshift(datetime(2020,1,1),'start','fortnight')",
    "dateshift(datetime(2020,1,1),'end','day')",
    "dateshift(datetime(2020,1,1),'start','month',1.5)",
    "between(1,2)",
    "between(datetime(2020,1,1),datetime(2020,3,1),'fortnights')",
    "caldays(1.5)",
    "caldays('a')",
    "calmonths(1) < calmonths(2)",
    "calmonths(1) * 1.5",
    "calmonths(1) - datetime(2020,1,1)",
    "split(calmonths(14))",
    "split(days(1.5), 'eons')",
    "calendarDuration(1,2)",
    "x = datetime(2020,1,1); x.Month = 'a';",
    "x = datetime(2020,1,1); x.Format = 5;",
    "x = [datetime(2020,1,1) datetime(2020,1,2)]; x.Day = [1 2 3];",
])
def test_errors_are_matlab_errors(code):
    with pytest.raises(EvalError):
        run(code)


def test_indexed_assignment_keeps_column_shape():
    assert num("t = datetime(2020,1,1)+days(0:2)'; t(2) = datetime(2000,1,1); v = [size(t) t(2).Year];") == [[3, 1, 2000]]
    assert num("t = datetime(2020,1,1)+days(0:2)'; t(5) = NaT; v = size(t);") == [[5, 1]]
    assert num("t = datetime(2020,1,1)+days(0:2)'; t(2,1) = '2001-01-01'; v = t(2).Year;") == [[2001]]
