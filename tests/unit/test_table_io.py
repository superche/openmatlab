"""readtable/writetable/readcell/writecell on delimited text (Epic #694)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


@pytest.fixture
def run(tmp_path):
    s = Session.create_default()
    r = ReplSession(s)

    def go(code):
        r.run_line(f"d = '{tmp_path.as_posix()}'; " + code)
        return s

    go.dir = tmp_path
    return go


def _num(s, name):
    return np.asarray(s.workspace.get(name).backend_buffer()).reshape(-1).tolist()


def _txt(s, name):
    return s.workspace.get(name).text


def test_types_and_missing(run):
    (run.dir / "a.csv").write_text("id,name,when,score\n1,ann,2020-01-02,3.5\n2,bob,,\n")
    s = run("T = readtable(fullfile(d,'a.csv')); c = class(T.when); n = isnat(T.when(2)); m = isnan(T.score(2)); "
            "k = iscell(T.name); i = T.id';")
    assert _txt(s, "c") == "datetime"
    assert _num(s, "n") == [True] and _num(s, "m") == [True] and _num(s, "k") == [True]
    assert _num(s, "i") == [1, 2]


def test_quoted_fields_and_names(run):
    (run.dir / "q.csv").write_text('first name,2nd\n"a, b",1\n')
    s = run("T = readtable(fullfile(d,'q.csv')); n = strjoin(T.Properties.VariableNames, ','); v = T.firstName{1};")
    assert _txt(s, "n") == "firstName,x2nd"
    assert _txt(s, "v") == "a, b"


def test_delimiter_sniff_and_no_header(run):
    (run.dir / "t.txt").write_text("1\t2\n3\t4\n")
    s = run("T = readtable(fullfile(d,'t.txt'), 'ReadVariableNames', false); v = T.Var2'; "
            "U = readtable(fullfile(d,'t.txt'), 'ReadVariableNames', false, 'VariableNames', {'a','b'}); w = U.a';")
    assert _num(s, "v") == [2, 4]
    assert _num(s, "w") == [1, 3]


def test_writetable_roundtrip_mixed(run):
    s = run("T = table([1;NaN], {'x, y';'z'}, string({'p';'q'}), categorical({'u';'v'}), 'VariableNames', {'a','b','c','g'}); "
            "f = fullfile(d,'o.csv'); writetable(T, f); txt = fileread(f); R = readtable(f); "
            "ok = isequal(R.b, T.b) && isnan(R.a(2)) && strcmp(R.g{2}, 'v');")
    assert _txt(s, "txt").splitlines()[:2] == ["a,b,c,g", '1,"x, y",p,u']
    assert _num(s, "ok") == [True]


def test_writetable_rownames_multicolumn_semicolon(run):
    s = run("T = table([1 2;3 4], 'RowNames', {'r1','r2'}); f = fullfile(d,'m.txt'); "
            "writetable(T, f, 'Delimiter', ';', 'WriteRowNames', true); txt = fileread(f);")
    assert _txt(s, "txt").splitlines() == ["Row;Var1_1;Var1_2", "r1;1;2", "r2;3;4"]


def test_readcell_writecell(run):
    s = run("f = fullfile(d,'c.csv'); writecell({1,'a b';2,''}, f); C = readcell(f); "
            "x = C{2,1}; y = C{1,2}; m = ismissing(C{2,2});")
    assert _num(s, "x") == [2]
    assert _txt(s, "y") == "a b"
    assert _num(s, "m") == [True]


@pytest.mark.parametrize("code", [
    "readtable(fullfile(d,'none.csv'))", "readtable(fullfile(d,'x.xlsx'))", "readtable(5)",
    "readtable(fullfile(d,'a.csv'), 'Nope', 1)", "writetable(5, 'z.csv')", "writecell(5, 'z.csv')",
    "writecell({{1}}, fullfile(d,'z.csv'))", "readtable(fullfile(d,'a.csv'), 'TextType', 'x')",
    "readtable(fullfile(d,'a.csv'), 'VariableNames', {'a'})",
])
def test_errors_are_matlab_errors(run, code):
    (run.dir / "a.csv").write_text("p,q\n1,2\n")
    s = run(f"try, {code}; e = 'none'; catch err, e = err.message; end")
    msg = _txt(s, "e")
    assert msg != "none" and "internal error" not in msg and "Traceback" not in msg
