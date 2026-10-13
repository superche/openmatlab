"""Epic #536: core string functions."""

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


def _t(s, n):
    return s.workspace.get(n).text


def _v(s, n):
    return np.asarray(s.workspace.get(n).backend_buffer())


def _cell(s, n):
    c = s.workspace.get(n)
    r, k = c.shape
    return [c.get(i, j).text for i in range(r) for j in range(k)]


def test_strsplit_collapse_and_options():
    s = _run("a = strsplit('a,b,,c', ','); b = strsplit('a,b,,c', ',', 'CollapseDelimiters', false); c = strsplit('a1b22c', '\\d+', 'DelimiterType', 'RegularExpression');")
    assert _cell(s, "a") == ["a", "b", "c"]
    assert _cell(s, "b") == ["a", "b", "", "c"]
    assert _cell(s, "c") == ["a", "b", "c"]


def test_strsplit_whitespace_default_keeps_edge_empties():
    s = _run("a = strsplit('  a  b ');")
    assert _cell(s, "a") == ["", "a", "b", ""]


def test_strjoin_default_custom_and_delimiter_cell():
    s = _run("a = strjoin({'x', 'y'}); b = strjoin({'x', 'y', 'z'}, '-'); c = strjoin({'a', 'b', 'c'}, {'-', '+'}); d = strjoin({'a', 'b'}, '\\n');")
    assert (_t(s, "a"), _t(s, "b"), _t(s, "c"), _t(s, "d")) == ("x y", "x-y-z", "a-b+c", "a\nb")
    with pytest.raises(Exception, match="one less"):
        _run("s = strjoin({'a'}, {'-'});")


def test_strfind_overlap_empty_and_cell():
    s = _run("a = strfind('aaa', 'aa'); b = isempty(strfind('abc', 'z')); c = strfind({'ab', 'ba'}, 'a');")
    assert _v(s, "a").tolist() == [[1, 2]] and _v(s, "b").item()
    cc = s.workspace.get("c")
    assert np.asarray(cc.get(0, 1).backend_buffer()).item() == 2


def test_strcat_trims_char_but_not_cells():
    s = _run("a = strcat('a ', 'b'); b = strcat({'a '}, 'b'); c = strcat(['a ';'bb'], 'x');")
    assert _t(s, "a") == "ab" and _cell(s, "b") == ["a b"]
    assert list(s.workspace.get("c").rows) == ["ax ", "bbx"]


def test_strvcat_skips_empty_and_pads():
    s = _run("q = strvcat('a', '', 'bcd');")
    assert list(s.workspace.get("q").rows) == ["a  ", "bcd"]


def test_str2num_ok_flag():
    s = _run("v = str2num('[1 2 3]'); [w, ok] = str2num('1+'); [x, ok2] = str2num('2*3');")
    assert _v(s, "v").tolist() == [[1, 2, 3]]
    assert not _v(s, "ok").item() and _v(s, "x").item() == 6 and _v(s, "ok2").item()


def test_mat2str_forms():
    s = _run("a = mat2str([1 2; 3 4]); b = mat2str([1.5 NaN; -Inf 2]); c = mat2str(true); d = mat2str(pi, 4); e = mat2str(int8([1 2]), 'class'); f = mat2str('it''s'); g = mat2str(zeros(0, 3));")
    assert [_t(s, n) for n in "abcdefg"] == ["[1 2;3 4]", "[1.5 NaN;-Inf 2]", "true", "3.142", "int8([1 2])", "'it''s'", "zeros(0,3)"]


def test_int2str_rounds_half_away():
    s = _run("a = int2str(2.5); b = int2str(-2.5); c = int2str([1.2 3.7]);")
    assert (_t(s, "a"), _t(s, "b"), _t(s, "c")) == ("3", "-3", "1  4")


def test_base_conversions():
    s = _run("a = dec2bin(5, 8); b = dec2bin([1 5]); c = dec2hex(255); d = hex2dec({'ff', '10'}); e = bin2dec('1010');")
    assert _t(s, "a") == "00000101" and list(s.workspace.get("b").rows) == ["001", "101"]
    assert _t(s, "c") == "FF" and _v(s, "d").reshape(-1).tolist() == [255, 16] and _v(s, "e").item() == 10
    with pytest.raises(Exception, match="invalid characters"):
        _run("x = bin2dec('12');")


def test_blanks_deblank_flip_char_and_cell():
    s = _run("a = blanks(3); b = deblank('ab   '); c = deblank({'a  ', 'b'}); d = fliplr('abc'); e = fliplr({1, 'a'});")
    assert _t(s, "a") == "   " and _t(s, "b") == "ab" and _cell(s, "c") == ["a", "b"]
    assert _t(s, "d") == "cba"
    assert s.workspace.get("e").get(0, 0).text == "a"
