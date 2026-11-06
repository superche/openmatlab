"""readtable Format for delimited text (#1042)."""

from __future__ import annotations

import csv
import io

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs.table_io import _split_detailed
from openmatlab.runtime.evaluator import EvalError
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


def _write(run, name, body):
    (run.dir / name).write_text(body)


def _col(s, table, i):
    return s.workspace.get(table).cols[i]


def test_quote_flags_follow_the_csv_splitter():
    lines = ['a,b', 'a,"b,c",d', '"a""b",c', 'a,,c', ',b', 'a,b,', ' "a",b', '"1",2']
    got = _split_detailed(lines, ",")
    exp = list(csv.reader(io.StringIO("\n".join(lines))))
    assert [[t for t, _q in row] for row in got] == exp
    assert [q for _t, q in got[-1]] == [True, False]


def test_documented_format_example(run):
    _write(run, "people.csv",
           "LastName,Gender,Age,Height,Weight,Smoker\n"
           "Smith,M,38,71,176,1\nJohnson,M,43,69,163,0\nWilliams,F,38,64,131,0\n")
    s = run("T = readtable(fullfile(d,'people.csv'), 'Format', '%s%s%u%f%f%s');"
            "n = strjoin(T.Properties.VariableNames, ',');")
    assert _txt(s, "n") == "LastName,Gender,Age,Height,Weight,Smoker"
    assert _col(s, "T", 0).matlab_class() == "cell"
    assert [_col(s, "T", 0).rows[i][0].text for i in range(3)] == ["Smith", "Johnson", "Williams"]
    assert [_col(s, "T", 1).rows[i][0].text for i in range(3)] == ["M", "M", "F"]
    age = np.asarray(_col(s, "T", 2).backend_buffer()).reshape(-1)
    assert _col(s, "T", 2).matlab_class() == "uint32"
    assert age.tolist() == [38, 43, 38]
    assert _col(s, "T", 3).matlab_class() == "double"
    assert np.asarray(_col(s, "T", 3).backend_buffer()).reshape(-1).tolist() == [71, 69, 64]
    assert [_col(s, "T", 5).rows[i][0].text for i in range(3)] == ["1", "0", "0"]


@pytest.mark.parametrize("fmt, kind, value", [
    ("%f", "double", 1.5),
    ("%n", "double", 1.5),
    ("%f64", "double", 1.5),
    ("%f32", "single", np.float32(1.5)),
    ("%d", "int32", 2),
    ("%u", "uint32", 2),
    ("%d8", "int8", 2),
    ("%u16", "uint16", 2),
    ("%u32", "uint32", 2),
])
def test_numeric_specifiers(run, fmt, kind, value):
    _write(run, "a.csv", "1.5\n")
    s = run(f"T = readtable(fullfile(d,'a.csv'), 'Format', '{fmt}', 'ReadVariableNames', false);")
    col = _col(s, "T", 0)
    assert col.matlab_class() == kind
    got = np.asarray(col.backend_buffer()).reshape(-1)[0]
    if kind in ("double", "single"):
        assert got == pytest.approx(float(value))
    else:
        assert int(got) == value


def test_integer_missing_saturates_and_a_bad_float_is_nan(run):
    _write(run, "a.csv", "abc\n1.5\n,\n300\n-1\n")
    s = run("U = readtable(fullfile(d,'a.csv'), 'Format', '%u8', 'ReadVariableNames', false);"
            "F = readtable(fullfile(d,'a.csv'), 'Format', '%f', 'ReadVariableNames', false);")
    assert np.asarray(_col(s, "U", 0).backend_buffer()).reshape(-1).tolist() == [0, 2, 0, 255, 0]
    floats = np.asarray(_col(s, "F", 0).backend_buffer()).reshape(-1)
    assert np.isnan(floats[0]) and floats[1] == pytest.approx(1.5) and np.isnan(floats[2])
    assert floats[3] == pytest.approx(300) and floats[4] == pytest.approx(-1)


def test_hex_and_binary(run):
    _write(run, "a.csv", "ff\n0xff\ngg\n")
    _write(run, "b.csv", "1010\n0b11\n")
    s = run("X = readtable(fullfile(d,'a.csv'), 'Format', '%x', 'ReadVariableNames', false);"
            "B = readtable(fullfile(d,'b.csv'), 'Format', '%b', 'ReadVariableNames', false);")
    assert _col(s, "X", 0).matlab_class() == "uint64"
    assert np.asarray(_col(s, "X", 0).backend_buffer()).reshape(-1).tolist() == [255, 255, 0]
    assert np.asarray(_col(s, "B", 0).backend_buffer()).reshape(-1).tolist() == [10, 3]


def test_width_precision_skip_and_quote(run):
    _write(run, "w.csv", "123.456\n")
    _write(run, "s.csv", "abcdefg,9\n")
    _write(run, "q.txt", 'name\n"ab""cd"\n')
    s = run("W = readtable(fullfile(d,'w.csv'), 'Format', '%5f', 'ReadVariableNames', false);"
            "P = readtable(fullfile(d,'w.csv'), 'Format', '%7.2f', 'ReadVariableNames', false);"
            "S = readtable(fullfile(d,'s.csv'), 'Format', '%*3s%f', 'ReadVariableNames', false);"
            "Q = readtable(fullfile(d,'q.txt'), 'Format', '%q');"
            "R = readtable(fullfile(d,'q.txt'), 'Format', '%s');"
            "wv = W.Var1; pv = P.Var1;")
    assert _num(s, "wv") == pytest.approx([123.4])
    assert _num(s, "pv") == pytest.approx([123.45])
    assert s.workspace.get("S").names == ["Var1"]
    assert np.asarray(_col(s, "S", 0).backend_buffer()).reshape(-1).tolist() == [9]
    assert _col(s, "Q", 0).rows[0][0].text == 'ab"cd'
    assert _col(s, "R", 0).rows[0][0].text == '"ab""cd"'


def test_datetime_specifiers_and_treat_as_missing(run):
    _write(run, "d.csv", "when\n2020-01-02\nhello\nNA\n")
    _write(run, "m.csv", "when\n01-Jan-2014\nbogus\n")
    _write(run, "n.csv", "a\n1\nNA\n3\n")
    s = run("D = readtable(fullfile(d,'d.csv'), 'Format', '%{yyyy-MM-dd}D', 'TreatAsMissing', 'NA');"
            "M = readtable(fullfile(d,'m.csv'), 'Format', '%D');"
            "N = readtable(fullfile(d,'n.csv'), 'Format', '%f', 'TreatAsMissing', 'NA');"
            "e = datetime(2020,1,2); j = datetime(2014,1,1);")
    got = np.asarray(_col(s, "D", 0).v).reshape(-1)
    assert _col(s, "D", 0).fmt == "yyyy-MM-dd"
    assert got[0] == np.asarray(s.workspace.get("e").v).reshape(-1)[0]
    assert np.isnan(got[1]) and np.isnan(got[2])
    month = np.asarray(_col(s, "M", 0).v).reshape(-1)
    assert month[0] == np.asarray(s.workspace.get("j").v).reshape(-1)[0]
    assert np.isnan(month[1])
    nums = np.asarray(_col(s, "N", 0).backend_buffer()).reshape(-1)
    assert nums[0] == 1 and np.isnan(nums[1]) and nums[2] == 3


def test_string_scalar_format_texttype_names_and_layout(run):
    _write(run, "a.csv", "a,b,c\n1,2,3\n4,5\n")
    _write(run, "t.csv", "a\nhi\n")
    s = run('A = readtable(fullfile(d,\'a.csv\'), "Format", "%f%*f%f", \'VariableNames\', {\'x\',\'z\'});'
            "B = readtable(fullfile(d,'t.csv'), 'Format', '%s', 'TextType', 'string');"
            "n = strjoin(A.Properties.VariableNames, ',');")
    assert _txt(s, "n") == "x,z"
    assert np.asarray(_col(s, "A", 0).backend_buffer()).reshape(-1).tolist() == [1, 4]
    z = np.asarray(_col(s, "A", 1).backend_buffer()).reshape(-1)
    assert z[0] == 3 and np.isnan(z[1])
    assert _col(s, "B", 0).is_string
    assert _col(s, "B", 0).matlab_class() == "string"


def test_header_delimiter_range_and_empty_explicit_format(run):
    _write(run, "s.txt", "# c\na b\n1 2\n3 4\n")
    _write(run, "r.csv", "skip,me\nid,name,score\n1,ann,10\n2,bob,20\n3,cy,30\n")
    _write(run, "e.csv", "")
    s = run("S = readtable(fullfile(d,'s.txt'), 'HeaderLines', 1, 'Delimiter', 'space', 'Format', ' %f %f ');"
            "R = readtable(fullfile(d,'r.csv'), 'Range', 'B2:C4', 'Format', '%s%f');"
            "E = readtable(fullfile(d,'e.csv'), 'Format', '%f%s');"
            "sv = S.b'; rv = R.score'; n = strjoin(R.Properties.VariableNames, ',');"
            "en = strjoin(E.Properties.VariableNames, ',');")
    assert _num(s, "sv") == [2, 4]
    assert _txt(s, "n") == "name,score"
    assert _num(s, "rv") == [10, 20]
    assert [s.workspace.get("R").cols[0].rows[i][0].text for i in range(2)] == ["ann", "bob"]
    assert s.workspace.get("E").nrows == 0
    assert _txt(s, "en") == "Var1,Var2"
    assert _col(s, "E", 0).matlab_class() == "double"
    assert _col(s, "E", 1).matlab_class() == "cell"


def test_auto_blank_quote_dates_and_ragged_lines(run):
    _write(run, "blank.csv", "id,score\n1,\n2,4\n")
    _write(run, "q.csv", 'a\n"1"\n"2"\n')
    _write(run, "date.csv", "when\n2020-01-02\n2020-03-04\n")
    _write(run, "hole.csv", "when,n\n2020-01-02,1\n,2\n")
    _write(run, "tok.csv", "a\n1\nNA\n3\n")
    _write(run, "wide.csv", "a,b\n1,2,3\n")
    _write(run, "glue.csv", "12abc,9\n7zz,8\n")
    s = run("B = readtable(fullfile(d,'blank.csv'), 'Format', 'AUTO');"
            "D0 = readtable(fullfile(d,'blank.csv'));"
            "Q = readtable(fullfile(d,'q.csv'), 'Format', 'auto');"
            "Q0 = readtable(fullfile(d,'q.csv'));"
            "H = readtable(fullfile(d,'date.csv'), 'Format', 'auto');"
            "H0 = readtable(fullfile(d,'date.csv'));"
            "O = readtable(fullfile(d,'hole.csv'), 'Format', 'auto');"
            "K = readtable(fullfile(d,'tok.csv'), 'Format', 'auto', 'TreatAsMissing', 'NA');"
            "G = readtable(fullfile(d,'glue.csv'), 'Format', 'auto', 'ReadVariableNames', false);")
    assert _col(s, "D0", 1).matlab_class() == "double"
    assert np.isnan(np.asarray(_col(s, "D0", 1).backend_buffer()).reshape(-1)[0])
    assert _col(s, "B", 1).matlab_class() == "cell"
    assert [_col(s, "B", 1).rows[i][0].text for i in range(2)] == ["", "4"]
    assert _col(s, "B", 0).matlab_class() == "double"
    assert _col(s, "Q", 0).matlab_class() == "cell"
    assert [_col(s, "Q", 0).rows[i][0].text for i in range(2)] == ["1", "2"]
    assert _col(s, "Q0", 0).matlab_class() == "double"
    assert _col(s, "H", 0).matlab_class() == "datetime"
    assert np.allclose(_col(s, "H", 0).v, _col(s, "H0", 0).v)
    assert _col(s, "O", 0).matlab_class() == "cell"
    assert _col(s, "O", 1).matlab_class() == "double"
    assert np.asarray(_col(s, "K", 0).backend_buffer()).reshape(-1).tolist()[0] == 1
    assert np.isnan(np.asarray(_col(s, "K", 0).backend_buffer()).reshape(-1)[1])
    assert len(s.workspace.get("G").names) == 2
    assert _col(s, "G", 0).matlab_class() == "cell"
    assert _col(s, "G", 1).matlab_class() == "double"
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'wide.csv'), 'Format', 'auto')")
    assert ei.value.identifier == "MATLAB:readtable:UnequalDelimiters"
    assert "Traceback" not in str(ei.value)


def test_header_only_auto_matches_default(run):
    _write(run, "h.csv", "a,b\n")
    s = run("A = readtable(fullfile(d,'h.csv'));"
            "B = readtable(fullfile(d,'h.csv'), 'Format', 'auto');")
    assert s.workspace.get("A").names == s.workspace.get("B").names == ["a", "b"]
    assert s.workspace.get("A").nrows == s.workspace.get("B").nrows == 0
    assert _col(s, "A", 0).matlab_class() == _col(s, "B", 0).matlab_class() == "cell"


def test_auto_matches_default_on_a_clean_file(run):
    _write(run, "a.csv", "id,name,when\n1,ann,2020-01-02\n2,bob,2020-03-04\n")
    s = run("A = readtable(fullfile(d,'a.csv'));"
            "B = readtable(fullfile(d,'a.csv'), 'Format', 'auto');")
    assert s.workspace.get("A").names == s.workspace.get("B").names
    for i in range(3):
        assert _col(s, "A", i).matlab_class() == _col(s, "B", i).matlab_class()
    assert np.allclose(_col(s, "A", 0).backend_buffer(), _col(s, "B", 0).backend_buffer())
    assert np.allclose(_col(s, "A", 2).v, _col(s, "B", 2).v)


def test_empty_auto_and_bad_format_are_eval_errors(run):
    _write(run, "a.csv", "a\n1\n")
    _write(run, "empty.csv", "\n")
    cases = [
        ("readtable(fullfile(d,'empty.csv'), 'Format', 'auto')", "MATLAB:readtable:NoData"),
        ("readtable(fullfile(d,'a.csv'), 'Format', 1)", "MATLAB:readtable:InvalidFormat"),
        ("readtable(fullfile(d,'a.csv'), 'Format', '')", "MATLAB:readtable:InvalidFormat"),
        ("readtable(fullfile(d,'a.csv'), 'Format', 'banana')", "MATLAB:readtable:InvalidFormat"),
        ("readtable(fullfile(d,'a.csv'), 'Format', '%C')", "MATLAB:readtable:InvalidFormat"),
        ("readtable(fullfile(d,'a.csv'), 'Format', '%{hh:mm:ss}T')", "MATLAB:readtable:InvalidFormat"),
        ("readtable(fullfile(d,'a.csv'), 'Format', '%[abc]')", "MATLAB:readtable:InvalidFormat"),
        ("readtable(fullfile(d,'a.csv'), 'Format', '%s,%f')", "MATLAB:readtable:InvalidFormat"),
        ("readtable(fullfile(d,'a.csv'), 'Format', '%*s')", "MATLAB:readtable:InvalidFormat"),
        ("readtable(fullfile(d,'a.csv'), 'Range', 'A1:B1', 'HeaderLines', 1, 'Format', '%f')",
         "MATLAB:textio:textio:InvalidRange"),
        ("readtable(fullfile(d,'a.csv'), 'MultipleDelimsAsOne', 1)", "MATLAB:textio:textio:UnknownParameter"),
    ]
    for code, ident in cases:
        with pytest.raises(EvalError) as ei:
            run(code)
        assert ei.value.identifier == ident
        assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)


def test_spreadsheet_is_rejected_before_the_file_is_opened(run):
    _write(run, "a.csv", "a\n1\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'));")
    for ext in (".xlsx", ".xls", ".xlsm", ".xlsb", ".ods"):
        with pytest.raises(EvalError) as ei:
            run(f"readtable(fullfile(d,'missing{ext}'), 'Format', '%f')")
        assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
        assert "Traceback" not in str(ei.value)
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.csv'), 'FileType', 'spreadsheet', 'Format', '%f')")
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.csv'), opts, 'Format', '%f')")
    assert ei.value.identifier == "MATLAB:textio:textio:UnknownParameter"
    assert s.workspace.get("opts").matlab_class() == "DelimitedTextImportOptions"
