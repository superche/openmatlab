"""Epic #539: containers.Map and date/time basics."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer())


def test_map_basic_ops_and_sorted_keys():
    s = _run("m = containers.Map(); m('b') = 2; m('a') = [1 2]; n = m.Count; k = keys(m); v = m('a'); h = isKey(m, {'a', 'z'}); remove(m, 'b'); n2 = length(m);")
    assert _v(s, "n").item() == 2 and _v(s, "v").tolist() == [[1, 2]]
    k = s.workspace.get("k")
    assert [k.get(0, j).text for j in range(2)] == ["a", "b"]
    assert _v(s, "h").tolist() == [[True, False]] and _v(s, "n2").item() == 1


def test_map_is_a_handle():
    s = _run("m = containers.Map(); m2 = m; m2('x') = 1; n = m.Count; c = class(m);")
    assert _v(s, "n").item() == 1 and s.workspace.get("c").text == "containers.Map"


def test_map_constructor_forms_and_types():
    s = _run("a = containers.Map({'x', 'y'}, {10, 20}); v = a('y'); kt = a.KeyType; b = containers.Map('KeyType', 'double', 'ValueType', 'any'); b(3) = 'three'; b(1) = 'one'; k = cell2mat(keys(b)); c = containers.Map([1 2], {'p', 'q'}); w = c(2);")
    assert _v(s, "v").item() == 20 and s.workspace.get("kt").text == "char"
    assert _v(s, "k").tolist() == [[1, 3]] and s.workspace.get("w").text == "q"


def test_map_errors():
    with pytest.raises(Exception, match="not present"):
        _run("m = containers.Map(); x = m('zz');")
    with pytest.raises(Exception, match="key type"):
        _run("m = containers.Map(); m(1) = 2;")
    with pytest.raises(Exception, match="value type"):
        _run("m = containers.Map('KeyType', 'double', 'ValueType', 'double'); m(1) = 'x';")
    with pytest.raises(Exception, match="same"):
        _run("m = containers.Map({'a', 'b'}, {1});")


def test_datetime_parts_arithmetic_and_rollover():
    s = _run("d = datetime(2020, 1, 31); d2 = d + days(1); m = month(d2); dd = day(d2); d3 = d + 1; e = day(d3); y = year(d); h = hour(datetime(2020, 1, 1, 13, 5, 0)); mi = minute(datetime(2020, 1, 1, 13, 5, 0));")
    assert (_v(s, "m").item(), _v(s, "dd").item(), _v(s, "e").item(), _v(s, "y").item()) == (2, 1, 1, 2020)
    assert _v(s, "h").item() == 13 and _v(s, "mi").item() == 5


def test_datetime_difference_comparison_and_errors():
    s = _run("n = days(datetime(2020, 3, 1) - datetime(2020, 2, 1)); c = datetime(2021, 1, 1) > datetime(2020, 12, 31); t = datetime('2020-03-04 10:00:00'); mo = month(t);")
    assert _v(s, "n").item() == 29 and _v(s, "c").item() and _v(s, "mo").item() == 3
    with pytest.raises(Exception, match="Addition of two datetime"):
        _run("z = datetime(2020, 1, 1) + datetime(2020, 1, 1);")


def test_duration_units_and_display():
    s = _run("a = minutes(seconds(90)); b = hours(days(1)); c = seconds(minutes(2) + seconds(30)); r = minutes(10) / minutes(5);")
    assert (_v(s, "a").item(), _v(s, "b").item(), _v(s, "c").item(), _v(s, "r").item()) == (1.5, 24, 150, 2)


def test_datenum_datestr_weekday_clock():
    s = _run("dn = datenum(2020, 1, 1) - datenum(2019, 1, 1); a = datenum(2020, 1, 1); ds = datestr(datenum(2020, 1, 2), 'yyyy-mm-dd'); dt = datestr(737791.5); w = weekday(datenum(2020, 1, 1)); c = clock; n = numel(c); m13 = datenum(2020, 13, 1) == datenum(2021, 1, 1);")
    assert _v(s, "dn").item() == 365 and _v(s, "a").item() == 737791
    assert s.workspace.get("ds").text == "2020-01-02" and s.workspace.get("dt").text == "01-Jan-2020 12:00:00"
    assert _v(s, "w").item() == 4 and _v(s, "n").item() == 6 and _v(s, "m13").item()


def test_seconds_display_has_no_float_truncation():
    from openmatlab.runtime.objects import datestr_format, datenum_from_parts

    assert datestr_format(datenum_from_parts(2020, 1, 31, 13, 5, 0), "HH:MM:SS") == "13:05:00"
