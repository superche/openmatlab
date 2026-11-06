"""readtable duration, categorical, logical, and more date formats (#1046)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
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


def _write(run, name, body):
    (run.dir / name).write_text(body)


def _col(s, table, i):
    return s.workspace.get(table).cols[i]


def _cell(col):
    return [col.rows[i][0].text for i in range(len(col.rows))]


def _nums(col):
    return np.asarray(col.backend_buffer()).reshape(-1)


def _days(col):
    return np.asarray(col.v).reshape(-1)


def _secs(days):
    return np.asarray(days, dtype=float) * 86400.0


def _dn(s, name):
    return float(np.asarray(s.workspace.get(name).v).reshape(-1)[0])


def test_duration_timer_text_and_outages_clock(run):
    _write(run, "a.csv",
           "when,elapsed,note\n"
           "2002-02-01 12:18,01:02:03,winter storm\n"
           "2002-02-07 16:50,1:00:54:21,equipment fault\n"
           ",,\n"
           "2004-04-06 05:44,-04:23:45,fire\n")
    _write(run, "f.csv", "elapsed\n00:05:23.867\n6:34:12\n")
    s = run("T = readtable(fullfile(d,'a.csv'));"
            "F = readtable(fullfile(d,'f.csv'));"
            "e = datetime(2002,2,1,12,18,0);"
            "opts = detectImportOptions(fullfile(d,'a.csv'));"
            "kinds = strjoin(opts.VariableTypes, ',');")
    assert _col(s, "T", 0).matlab_class() == "datetime"
    assert _col(s, "T", 0).fmt == "yyyy-MM-dd HH:mm"
    assert np.asarray(_col(s, "T", 0).v).reshape(-1)[0] == _dn(s, "e")
    assert np.isnan(np.asarray(_col(s, "T", 0).v).reshape(-1)[2])
    assert _col(s, "T", 1).matlab_class() == "duration"
    assert _col(s, "T", 1).fmt == "hh:mm:ss"
    got = _secs(_days(_col(s, "T", 1)))
    assert got[0] == pytest.approx(1 * 3600 + 2 * 60 + 3)
    assert got[1] == pytest.approx(24 * 3600 + 54 * 60 + 21)
    assert np.isnan(got[2])
    assert got[3] == pytest.approx(-(4 * 3600 + 23 * 60 + 45))
    assert _cell(_col(s, "T", 2)) == ["winter storm", "equipment fault", "", "fire"]
    frac = _secs(_days(_col(s, "F", 0)))
    assert frac[0] == pytest.approx(5 * 60 + 23.867)
    assert frac[1] == pytest.approx(6 * 3600 + 34 * 60 + 12)
    assert s.workspace.get("kinds").text == "datetime,duration,char"


def test_readcell_uses_the_same_single_field_dates(run):
    _write(run, "a.csv", "01/02/2021,15/03/2021,2002-02-01 12:18\n")
    s = run("C = readcell(fullfile(d,'a.csv'));"
            "a = C{1}; b = C{2}; c = C{3};"
            "e = datetime(2021,1,2); f = datetime(2021,3,15); g = datetime(2002,2,1,12,18,0);")
    assert _col_class(s, "a") == _col_class(s, "b") == _col_class(s, "c") == "datetime"
    assert _dn(s, "a") == _dn(s, "e")
    assert _dn(s, "b") == _dn(s, "f")
    assert _dn(s, "c") == _dn(s, "g")


def _col_class(s, name):
    return s.workspace.get(name).matlab_class()


def test_two_part_time_and_leading_plus_stay_text(run):
    _write(run, "a.csv", "clock,plus\n12:30,+01:00:00\n01:15,+00:30:00\n")
    s = run("T = readtable(fullfile(d,'a.csv'));")
    assert _col(s, "T", 0).matlab_class() == _col(s, "T", 1).matlab_class() == "cell"
    assert _cell(_col(s, "T", 0)) == ["12:30", "01:15"]


def test_duration_type_text_and_placeholders(run):
    _write(run, "a.csv", "elapsed,id\n01:00:00,1\nNA,2\n00:30:00,3\n")
    s = run("A = readtable(fullfile(d,'a.csv'), 'TreatAsMissing', 'NA');"
            "B = readtable(fullfile(d,'a.csv'));"
            "C = readtable(fullfile(d,'a.csv'), 'DurationType', 'text', 'TreatAsMissing', 'NA');"
            "D = readtable(fullfile(d,'a.csv'), 'DurationType', 'TEXT', 'TextType', 'string',"
            " 'TreatAsMissing', 'NA');"
            "m = double(ismissing(A.elapsed)');"
            "opts = detectImportOptions(fullfile(d,'a.csv'), 'DurationType', 'text');"
            "k = opts.VariableTypes{1};")
    assert _col(s, "A", 0).matlab_class() == "duration"
    assert _col(s, "A", 1).matlab_class() == "double"
    assert list(_nums(_col(s, "A", 1))) == [1, 2, 3]
    assert np.isnan(_secs(_days(_col(s, "A", 0)))[1])
    assert list(_nums(s.workspace.get("m"))) == [0, 1, 0]
    assert _col(s, "B", 0).matlab_class() == "cell"
    assert _cell(_col(s, "C", 0)) == ["01:00:00", "", "00:30:00"]
    assert _col(s, "D", 0).matlab_class() == "string"
    assert s.workspace.get("k").text == "char"


def test_format_auto_keeps_duration_as_text_and_reads_the_new_dates(run):
    _write(run, "a.csv", "when,elapsed\n2002-02-01 12:18,01:02:03\n2002-02-07 16:50,04:05:06\n")
    s = run("A = readtable(fullfile(d,'a.csv'));"
            "B = readtable(fullfile(d,'a.csv'), 'Format', 'auto');")
    assert _col(s, "A", 0).matlab_class() == _col(s, "B", 0).matlab_class() == "datetime"
    assert _col(s, "A", 1).matlab_class() == "duration"
    assert _col(s, "B", 1).matlab_class() == "cell"
    assert _cell(_col(s, "B", 1)) == ["01:02:03", "04:05:06"]


def test_slash_and_year_first_dates(run):
    _write(run, "us.csv", "when\n01/14/2018\n2/23/2018\n")
    _write(run, "dm.csv", "when\n15/03/2021\n01/02/2021\n")
    _write(run, "mix.csv", "when\n01/15/2021\n15/01/2021\n")
    _write(run, "amb.csv", "when\n01/02/2021\n03/04/2021\n")
    _write(run, "y.csv", "when\n2020/01/02 03:04\n2020/3/4\n")
    _write(run, "old.csv", "when\n01-Jan-2020\n1-Jan-2020 12:18\n")
    s = run("U = readtable(fullfile(d,'us.csv'));"
            "M = readtable(fullfile(d,'dm.csv'));"
            "X = readtable(fullfile(d,'mix.csv'));"
            "A = readtable(fullfile(d,'amb.csv'));"
            "Y = readtable(fullfile(d,'y.csv'));"
            "O = readtable(fullfile(d,'old.csv'));"
            "u = datetime(2018,1,14); v = datetime(2018,2,23);"
            "p = datetime(2021,3,15); q = datetime(2021,2,1);"
            "r = datetime(2021,1,2); t = datetime(2021,3,4);")
    assert _col(s, "U", 0).fmt == "MM/dd/yyyy"
    assert np.asarray(_col(s, "U", 0).v).reshape(-1)[0] == _dn(s, "u")
    assert np.asarray(_col(s, "U", 0).v).reshape(-1)[1] == _dn(s, "v")
    assert _col(s, "M", 0).fmt == "dd/MM/yyyy"
    assert np.asarray(_col(s, "M", 0).v).reshape(-1)[0] == _dn(s, "p")
    assert np.asarray(_col(s, "M", 0).v).reshape(-1)[1] == _dn(s, "q")
    assert _col(s, "X", 0).matlab_class() == "cell"
    assert _col(s, "A", 0).fmt == "MM/dd/yyyy"
    assert np.asarray(_col(s, "A", 0).v).reshape(-1)[0] == _dn(s, "r")
    assert np.asarray(_col(s, "A", 0).v).reshape(-1)[1] == _dn(s, "t")
    assert _col(s, "Y", 0).matlab_class() == "cell"  # 03:04 and a date-only row are two forms
    assert _col(s, "O", 0).matlab_class() == "cell"  # date-only and HH:mm are two forms


def test_one_slash_family_with_a_clock(run):
    _write(run, "a.csv", "when\n2020/01/02\n2020/3/4\n")
    _write(run, "b.csv", "when\n01-Jan-2020 12:18\n02-Feb-2020 07:08\n")
    _write(run, "c.csv", "when\n2020-01-02 03:04:05\n2020-3-4\n")
    s = run("A = readtable(fullfile(d,'a.csv'));"
            "B = readtable(fullfile(d,'b.csv'));"
            "C = readtable(fullfile(d,'c.csv'));"
            "H = readtable(fullfile(d,'b.csv'), 'DatetimeType', 'text');"
            "e = datetime(2020,1,2);")
    assert _col(s, "A", 0).matlab_class() == "datetime"
    assert _col(s, "A", 0).fmt == "yyyy/MM/dd"
    assert np.asarray(_col(s, "A", 0).v).reshape(-1)[0] == _dn(s, "e")
    assert _col(s, "B", 0).fmt == "dd-MMM-yyyy HH:mm"
    assert _col(s, "C", 0).matlab_class() == "cell"
    assert _cell(_col(s, "H", 0)) == ["01-Jan-2020 12:18", "02-Feb-2020 07:08"]


def test_logical_and_categorical_are_typed_from_field_text(run):
    _write(run, "a.csv", "flag,region,id\nTRUE,South,1\nfalse,North,0\nt,South,2\nF,,3\nno,unknown,4\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'));"
            "seen = strjoin(opts.VariableTypes, ',');"
            "opts = setvaropts(opts, 'flag', 'Type', 'logical');"
            "opts = setvaropts(opts, 'region', 'Type', 'categorical', 'TreatAsMissing', 'unknown');"
            "T = readtable(fullfile(d,'a.csv'), opts);"
            "U = readtable(fullfile(d,'a.csv'));"
            "m = double(ismissing(T.region)');")
    assert s.workspace.get("seen").text == "char,char,double"
    assert list(_nums(_col(s, "U", 2))) == [1, 0, 2, 3, 4]
    assert _col(s, "U", 0).matlab_class() == "cell"
    flag = _nums(_col(s, "T", 0))
    assert _col(s, "T", 0).matlab_class() == "logical"
    assert flag.tolist() == [True, False, True, False, False]
    assert _col(s, "T", 1).matlab_class() == "categorical"
    assert _col(s, "T", 1).cats == ["North", "South"]
    assert _col(s, "T", 1).codes.reshape(-1).tolist() == [2, 1, 2, 0, 0]
    assert list(_nums(s.workspace.get("m"))) == [0, 0, 0, 1, 1]
    assert list(_nums(_col(s, "T", 2))) == [1, 0, 2, 3, 4]


def test_variabletypes_and_format_specifiers(run):
    _write(run, "a.csv", "elapsed,label,clock,mins\n6:34:12,b,1:30,78:34\n,a,2:00,1:02\n78:34,b,9:15,00:30\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'));"
            "opts.VariableTypes = {'duration','categorical','char','char'};"
            "T = readtable(fullfile(d,'a.csv'), opts);"
            "F = readtable(fullfile(d,'a.csv'), 'Format', '%T %C %{hh:mm}T %{mm:ss}T');"
            "G = readtable(fullfile(d,'a.csv'), 'Format', '%T %s %s %s', 'DurationType', 'text');"
            "one = seconds(F.elapsed(1));")
    assert _col(s, "T", 0).matlab_class() == "duration"
    forced = _secs(_days(_col(s, "T", 0)))
    assert forced[0] == pytest.approx(6 * 3600 + 34 * 60 + 12)
    assert np.isnan(forced[1])
    assert np.isnan(forced[2])  # 78:34 is not hh:mm:ss
    assert _col(s, "T", 1).cats == ["a", "b"]
    assert _col(s, "T", 1).codes.reshape(-1).tolist() == [2, 1, 2]
    spec = _secs(_days(_col(s, "F", 0)))
    assert spec[0] == pytest.approx(6 * 3600 + 34 * 60 + 12)
    assert np.isnan(spec[2])
    assert _col(s, "F", 1).codes.reshape(-1).tolist() == [2, 1, 2]
    assert _secs(_days(_col(s, "F", 2)))[0] == pytest.approx(90 * 60)
    assert _secs(_days(_col(s, "F", 3)))[0] == pytest.approx(78 * 60 + 34)
    assert _col(s, "G", 0).matlab_class() == "cell"
    assert _cell(_col(s, "G", 0))[0] == "6:34:12"
    assert float(np.asarray(s.workspace.get("one").backend_buffer()).reshape(-1)[0]) == pytest.approx(spec[0])


def test_explicit_date_format_and_numeric_column_are_unchanged(run):
    _write(run, "a.csv", "when,n\n15/03/2021,01:02:03\n01/04/2021,4\n")
    s = run("A = readtable(fullfile(d,'a.csv'), 'Format', '%{dd/MM/yyyy}D %f');"
            "B = readtable(fullfile(d,'a.csv'));"
            "e = datetime(2021,3,15);")
    assert _col(s, "A", 0).matlab_class() == "datetime"
    assert np.asarray(_col(s, "A", 0).v).reshape(-1)[0] == _dn(s, "e")
    assert np.isnan(_nums(_col(s, "A", 1))[0])
    assert _col(s, "B", 1).matlab_class() == "cell"  # a timer and a number do not share a type


def test_rewritten_header_still_keeps_the_original_text(run):
    _write(run, "a.csv", "elapsed (h),id\n01:00:00,1\n02:00:00,2\n")
    s = run("T = readtable(fullfile(d,'a.csv'));"
            "opts = detectImportOptions(fullfile(d,'a.csv'));"
            "U = readtable(fullfile(d,'a.csv'), opts);")
    assert s.workspace.get("T").names[0] != "elapsed (h)"
    assert s.workspace.get("T").variable_descriptions[0] == "elapsed (h)"
    assert _col(s, "T", 0).matlab_class() == _col(s, "U", 0).matlab_class() == "duration"
    assert s.workspace.get("U").variable_descriptions[0] == "elapsed (h)"


def test_bad_duration_type_and_spreadsheet_are_eval_errors(run):
    _write(run, "a.csv", "elapsed\n01:00:00\n")
    s = run("opts = detectImportOptions(fullfile(d,'a.csv'));")
    cases = [
        ("readtable(fullfile(d,'a.csv'), 'DurationType', 'hours')", "MATLAB:readtable:InvalidDurationType"),
        ("readtable(fullfile(d,'a.csv'), 'DurationType', 1)", "MATLAB:readtable:InvalidDurationType"),
        ("detectImportOptions(fullfile(d,'missing.csv'), 'DurationType', 'nope')",
         "MATLAB:readtable:InvalidDurationType"),
        ("readtable(fullfile(d,'a.csv'), opts, 'DurationType', 'text')", "MATLAB:textio:textio:UnknownParameter"),
        ("setvaropts(opts, 'DurationType', 'text')", "MATLAB:setvaropts:UnknownParameter"),
        ("opts.DurationType = 'text';", "MATLAB:noPublicFieldForClass"),
    ]
    for code, ident in cases:
        with pytest.raises(EvalError) as ei:
            run(code)
        assert ei.value.identifier == ident
        assert "Traceback" not in str(ei.value) and "internal error" not in str(ei.value)
    for ext in (".xlsx", ".xls", ".xlsm", ".xlsb", ".ods"):
        with pytest.raises(EvalError) as ei:
            run(f"readtable(fullfile(d,'missing{ext}'), 'DurationType', 'nope')")
        assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
        assert not (run.dir / f"missing{ext}").exists()
    with pytest.raises(EvalError) as ei:
        run("readtable(fullfile(d,'a.csv'), 'FileType', 'spreadsheet', 'DurationType', 'text')")
    assert ei.value.identifier == "MATLAB:readtable:UnsupportedFileType"
    with pytest.raises(EvalError) as ei:
        run("detectImportOptions(fullfile(d,'missing.xlsx'), 'DurationType', 'text')")
    assert ei.value.identifier == "MATLAB:detectImportOptions:UnsupportedFileType"
    assert s.workspace.get("opts").variables[0].type == "duration"
